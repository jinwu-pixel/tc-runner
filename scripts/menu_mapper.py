"""
Settings Menu Mapper (catalog schema v0.2 — raw inventory helper).

This tool is auxiliary to hand-written catalog MD entries. It outputs:
- Raw uiautomator dump + label inventory of one screen (inventory mode)
- DFS walk of screen fingerprint tree (dfs mode, DEPRECATED per v0.2)

Catalog MD is hand-written. menu_mapper.py outputs (`menu_tree_<ts>.json/md`)
are auxiliary references — do not check them in as catalog entries.

DFS + --allow-tap requires explicit --i-understand-risk opt-in.
Per catalog_schema.md v0.2, DFS mode is DEPRECATED for normal operations.
"""

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime
from xml.etree import ElementTree as ET
import sys

# Ensure src modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.adb import ADB

# DENYLIST — catalog schema v0.2 통합 (사용자 가드 키워드 포함).
# 변경 시 THOR2_K - Settings/catalog_schema.md §14와 양쪽 동기.
DENYLIST = [
    # 일본어
    "緊急", "SOS", "発信", "電話", "メッセージ送信", "初期化", "リセット", "削除", "消去",
    "許可", "拒否", "保存", "変更", "アカウント", "パスワード", "PIN", "ロック", "開発者向け",
    "通話", "通信", "緊急通報", "アップデート", "録音",
    # 한국어
    "긴급", "전화", "메시지", "초기화", "삭제", "허용", "거부", "결제", "비밀번호", "잠금",
    "공장초기화", "발신", "발송", "녹음", "촬영", "업데이트",
    # 영어
    "reset", "delete", "emergency", "call", "message", "permission", "allow", "deny",
    "developer", "factory", "payment", "uninstall", "remove", "clear data", "update", "OTA",
    "record", "capture", "shutter", "fota", "force stop",
]

# ALLOWLIST_PACKAGES — catalog schema v0.2 정합 (THOR2 pilot 결과 반영).
# 변경 시 catalog_schema.md §15와 양쪽 동기.
ALLOWLIST_PACKAGES = [
    "com.android.settings",
    "com.hnlens.simplemode",
    "com.hnlens.calculator",
    "com.hnlens.clock",
    "com.hnlens.magnifying",
    "com.hnlens.pedometer",
    "com.hnlens.fmradio",
    "com.hnlens.soundrecorder",
    "com.hnlens.camera",
    "com.hnlens.lssys",
    "com.hnlens.wallpaper",
    "com.hnlens.lsoqc",
    "com.hnlens.contacts",  # 진입 가드는 별도 (DENYLIST 키워드)
    "com.google.android.apps.wellbeing",  # 외부, Settings 통합 entry
    "com.google.android.permissioncontroller",  # HOME_SETTINGS 라우팅
    "com.mediatek.duraspeed",  # OEM
]


def parse_bounds(bounds_str: str):
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str or "")
    if not match:
        return None
    x1, y1, x2, y2 = map(int, match.groups())
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def extract_nodes(xml_str: str):
    try:
        start_idx = xml_str.find("<?xml")
        if start_idx != -1:
            xml_str = xml_str[start_idx:]
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        print(f"Failed to parse XML: {e}")
        return []
    nodes = []
    parent_map = {c: p for p in root.iter() for c in p}
    for elem in root.iter("node"):
        attrib = dict(elem.attrib)
        curr = elem
        is_clickable = False
        is_focusable = False
        while curr is not None:
            if curr.attrib.get("clickable") == "true":
                is_clickable = True
            if curr.attrib.get("focusable") == "true":
                is_focusable = True
            if is_clickable and is_focusable:
                break
            curr = parent_map.get(curr)
        attrib["inherited_clickable"] = "true" if is_clickable else "false"
        attrib["inherited_focusable"] = "true" if is_focusable else "false"
        nodes.append(attrib)
    return nodes


def generate_fingerprint(current_focus: str, nodes: list) -> str:
    texts = [n.get("text", "") for n in nodes if n.get("text")]
    rids = [n.get("resource-id", "") for n in nodes if n.get("resource-id")]
    raw_str = current_focus + "|" + "|".join(sorted(texts)) + "|" + "|".join(sorted(rids))
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()[:8]


def is_node_safe(node: dict) -> tuple[bool, str]:
    if node.get("checkable") == "true":
        return False, "checkable=true"
    if node.get("class") in ["android.widget.Switch", "android.widget.CheckBox", "android.widget.RadioButton"]:
        return False, "switch/checkbox/radio"
    text = node.get("text", "")
    content_desc = node.get("content-desc", "")
    label = text if text else content_desc
    if not label:
        return False, "no_label"
    for deny in DENYLIST:
        if deny.lower() in label.lower():
            return False, f"denylist_match_{deny}"
    if node.get("clickable") == "true" or node.get("focusable") == "true" or \
       node.get("inherited_clickable") == "true" or node.get("inherited_focusable") == "true":
        return True, "ok"
    return False, "not_clickable_or_focusable"


class MenuMapper:
    def __init__(self, adb: ADB, args):
        self.adb = adb
        self.args = args
        self.visited_fingerprints = set()
        self.tree_output = {"root": args.package, "nodes": []}
        self.markdown_lines = []
        
        # Summary Statistics
        self.stats = {
            "mode": args.mode,
            "package": args.package,
            "max_depth": args.max_depth,
            "visited_screen_count": 0,
            "clicked_node_count": 0,
            "skipped_risk_count": 0,
            "blocked_external_count": 0,
            "duplicate_skipped_count": 0,
            "back_success_count": 0,
            "back_fail_count": 0,
            "max_depth_cutoff_count": 0,
            "output_md": "",
            "output_json": ""
        }

    def get_current_focus(self) -> str:
        out = self.adb.shell("dumpsys window | grep mCurrentFocus")
        if "mCurrentFocus" in out:
            match = re.search(r" u0 ([\w\.]+)/([\w\.]+)", out)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
            match = re.search(r" ([\w\.]+)/([\w\.]+)", out)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        return "unknown/unknown"

    def parse_bounds(self, bounds_str: str):
        return parse_bounds(bounds_str)

    def extract_nodes(self, xml_str: str):
        return extract_nodes(xml_str)

    def generate_fingerprint(self, current_focus: str, nodes: list) -> str:
        return generate_fingerprint(current_focus, nodes)

    def is_node_safe(self, node: dict) -> tuple[bool, str]:
        return is_node_safe(node)

    def print_summary(self):
        print("\n=== Menu Mapper Summary ===")
        for k, v in self.stats.items():
            print(f"{k}: {v}")
        print("===========================\n")

    def format_summary_md(self):
        lines = ["## Summary", "```yaml"]
        for k, v in self.stats.items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        return "\n".join(lines)

    def run_inventory(self):
        print("Running Inventory Pass...")
        xml_str = self.adb.dump_ui()
        focus = self.get_current_focus()
        nodes = self.extract_nodes(xml_str)
        fp = self.generate_fingerprint(focus, nodes)
        self.stats["visited_screen_count"] += 1
        
        print(f"Current Focus: {focus}")
        print(f"Fingerprint: {fp}")
        
        for node in nodes:
            safe, reason = self.is_node_safe(node)
            label = node.get("text") or node.get("content-desc", "")
            if safe:
                print(f"  [O] {label} (Class: {node.get('class')})")
            elif label:
                print(f"  [X] {label} (Reason: {reason})")
                if "denylist" in reason:
                    self.stats["skipped_risk_count"] += 1

        self.save_output("inventory", {"focus": focus, "fingerprint": fp, "nodes": nodes})
        self.print_summary()

    def run_dfs(self, current_depth=1, parent_tree=None, parent_md_indent=""):
        xml_str = self.adb.dump_ui()
        focus = self.get_current_focus()
        nodes = self.extract_nodes(xml_str)
        fp = self.generate_fingerprint(focus, nodes)
        
        pkg = focus.split("/")[0] if "/" in focus else focus
        if pkg not in ALLOWLIST_PACKAGES:
            self.stats["blocked_external_count"] += 1
            return fp, "BLOCKED_EXTERNAL_PACKAGE"
            
        if fp in self.visited_fingerprints:
            self.stats["duplicate_skipped_count"] += 1
            return fp, "DUPLICATE_SKIPPED"
            
        self.visited_fingerprints.add(fp)
        self.stats["visited_screen_count"] += 1
        
        candidates = []
        for node in nodes:
            safe, reason = self.is_node_safe(node)
            if safe:
                candidates.append(node)
            elif node.get("text") or node.get("content-desc"):
                if "denylist" in reason or "checkable" in reason or "switch" in reason:
                    label = node.get("text") or node.get("content-desc")
                    self.stats["skipped_risk_count"] += 1
                    self.markdown_lines.append(f"{parent_md_indent}- {label}")
                    self.markdown_lines.append(f"{parent_md_indent}  - action: none")
                    self.markdown_lines.append(f"{parent_md_indent}  - source_fp: {fp}")
                    self.markdown_lines.append(f"{parent_md_indent}  - result: [SKIPPED_RISK] {reason}")
                    if parent_tree is not None:
                        parent_tree.append({"label": label, "skipped": True, "reason": reason, "source_fp": fp})

        if current_depth > self.args.max_depth:
            self.stats["max_depth_cutoff_count"] += 1
            return fp, "MAX_DEPTH_CUTOFF"

        for node in candidates:
            label = node.get("text") or node.get("content-desc")
            bounds = node.get("bounds")
            center = self.parse_bounds(bounds)
            if not center:
                continue
                
            tree_node = {
                "label": label,
                "package_activity": focus,
                "node_type": node.get("class"),
                "source_fp": fp,
                "action": "tap",
                "children": []
            }
            if parent_tree is not None:
                parent_tree.append(tree_node)

            if not self.args.allow_tap:
                self.markdown_lines.append(f"{parent_md_indent}- {label}")
                self.markdown_lines.append(f"{parent_md_indent}  - action: none")
                self.markdown_lines.append(f"{parent_md_indent}  - source_fp: {fp}")
                self.markdown_lines.append(f"{parent_md_indent}  - result: INVENTORY_ONLY")
                continue
                
            self.stats["clicked_node_count"] += 1
            print(f"[{current_depth}/{self.args.max_depth}] Tapping: {label}")
            if self.args.use_dpad:
                self.adb.shell(f"input tap {center[0]} {center[1]}")
            else:
                self.adb.shell(f"input tap {center[0]} {center[1]}")
            
            time.sleep(1.0)
            
            target_fp, result = self.run_dfs(current_depth + 1, tree_node["children"], parent_md_indent + "  ")
            
            tree_node["target_fp"] = target_fp
            tree_node["result"] = result
            
            self.markdown_lines.append(f"{parent_md_indent}- {label}")
            self.markdown_lines.append(f"{parent_md_indent}  - action: tap")
            self.markdown_lines.append(f"{parent_md_indent}  - source_fp: {fp}")
            if target_fp:
                self.markdown_lines.append(f"{parent_md_indent}  - target_fp: {target_fp}")
            self.markdown_lines.append(f"{parent_md_indent}  - result: {result}")
            
            # Save partial
            self.save_output("dfs", self.tree_output)
            
            # Back
            if result not in ["DUPLICATE_SKIPPED", "MAX_DEPTH_CUTOFF"]:
                print(f"Going back from: {label}")
                self.adb.shell("input keyevent 4")
                time.sleep(1.0)
                
                new_focus = self.get_current_focus()
                new_pkg = new_focus.split("/")[0] if "/" in new_focus else new_focus
                if new_pkg not in ALLOWLIST_PACKAGES:
                    self.adb.shell("input keyevent 4")
                    time.sleep(1.0)
                
                # Check if back was successful by checking focus or just count it
                final_focus = self.get_current_focus()
                if final_focus == focus:
                    self.stats["back_success_count"] += 1
                else:
                    self.stats["back_fail_count"] += 1

        return fp, "ENTERED"

    def save_output(self, mode: str, data: dict):
        os.makedirs(self.args.out_dir, exist_ok=True)
        if not hasattr(self, 'ts'):
            self.ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        ts = self.ts
        
        json_path = os.path.join(self.args.out_dir, f"menu_tree_settings_{ts}.json")
        md_path = os.path.join(self.args.out_dir, f"menu_tree_settings_{ts}.md")
        
        self.stats["output_md"] = md_path
        self.stats["output_json"] = json_path

        data["summary"] = self.stats

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Settings Menu Tree — AT-M140 ja-JP\n\n")
            f.write(self.format_summary_md() + "\n\n")
            f.write("\n".join(self.markdown_lines))

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Settings Menu Mapper (raw inventory helper, catalog schema v0.2).\n"
            "Outputs raw dump + label inventory. Catalog MD is hand-written — "
            "this tool is auxiliary only. DFS / --allow-tap is DEPRECATED per v0.2 "
            "(운영 가드 위반 — opt-in 필요)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--package", default="com.android.settings",
                        help="Target package (ALLOWLIST_PACKAGES 외 진입 시 차단)")
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--out-dir", default="outputs",
                        help="Raw inventory output dir (catalog MD 영역과 분리)")
    parser.add_argument("--mode", choices=["inventory", "dfs"], default="inventory",
                        help="inventory (단발 dump, 권고) / dfs (자동 walk, DEPRECATED)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-tap", action="store_true",
                        help="[DEPRECATED v0.2] 자동 탭 활성. toggle/삭제/촬영 등 위험 동작 가능. "
                             "운영 가드 위반 — 사용 시 --i-understand-risk 명시 필요.")
    parser.add_argument("--i-understand-risk", action="store_true",
                        help="--allow-tap 사용 시 위험 명시 opt-in. 미사용 시 --allow-tap 차단.")
    parser.add_argument("--use-dpad", action="store_true",
                        help="(현재 미구현 — input tap fallback)")
    parser.add_argument("--serial", help="ADB device serial (multi-device 환경)")
    args = parser.parse_args()

    adb = ADB(device_serial=args.serial)
    mapper = MenuMapper(adb, args)

    if args.mode == "inventory":
        mapper.run_inventory()
    else:
        # DFS 모드 — catalog schema v0.2에서 DEPRECATED. opt-in 가드.
        if args.allow_tap and not args.i_understand_risk:
            print(
                "ERROR: --allow-tap is DEPRECATED per catalog schema v0.2.\n"
                "Automated tapping can trigger toggles/captures/uninstalls/calls.\n"
                "To proceed, explicitly add --i-understand-risk.",
                file=sys.stderr,
            )
            sys.exit(2)
        if not args.allow_tap:
            print(
                "WARNING: DFS mode without --allow-tap = fingerprint walk only (no taps). "
                "DFS itself is DEPRECATED per catalog schema v0.2.",
                file=sys.stderr,
            )
        if args.allow_tap and args.i_understand_risk:
            print(
                "WARNING: --allow-tap with --i-understand-risk acknowledged.\n"
                "Operator accepts risk of automated UI interaction (DENYLIST applied).",
                file=sys.stderr,
            )
        print(f"Starting DFS Mapper (Max Depth: {args.max_depth}, Tap Allowed: {args.allow_tap})")
        adb.shell(f"monkey -p {args.package} -c android.intent.category.LAUNCHER 1")
        time.sleep(2)
        mapper.markdown_lines.append(f"- {args.package}")
        mapper.run_dfs(current_depth=1, parent_tree=mapper.tree_output["nodes"], parent_md_indent="  ")
        mapper.save_output("dfs", mapper.tree_output)
        mapper.print_summary()

if __name__ == "__main__":
    main()
