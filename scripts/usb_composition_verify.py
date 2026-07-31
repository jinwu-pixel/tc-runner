#!/usr/bin/env python3
"""USB composition 재부팅 유지 검증 — read-only 캡처/채점 harness (BTS#25462).

이 도구는 *읽기 전용* 이다. composition 변경 / reboot / setprop / svc / install 같은
mutating 동작은 절대 수행하지 않는다 — 그건 사용자가 직접 몰고(승인영역), 본 harness 는
판정 신호(3-Way ground truth)만 찍어 채점한다.

판정 프레임 (TC_BTS25462.md §2):
  W2 persist : getprop persist.sys.usb.config  == 선택 조합 full func string
  W3 active  : getprop sys.usb.config           == 선택 조합  + 부팅 로그 복원체인
  qmmi 기본  : getprop sys.usb.qmmi.func        (재부팅 복귀 fallback)
  data       : dumpsys telephony.registry / ip / ping  (composition별 데이터 무결성)
  host ports : Get-PnpDevice (Windows)          (포트 매핑 — MODEM=serial_cdev)

서브커맨드 (전부 read-only):
  preflight            모델/빌드/carrier/USB props 확인 + wrong-device 가드
  snapshot <label>     체크포인트 1회 캡처 → evidence/<label>/snapshot.json
  judge <pre> <post> --expect "diag,serial_cdev,..."   유지 판정
  ports                호스트 USB 포트 enumerate (Windows)
  selftest             단말 없이 순수 함수 자가검증

serial 고정: --serial 또는 env USB_DEV (wrong-device 가드).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

# ---- function-string -> 표시명 매핑 (TC_BTS25462.md §1, 단말 실측) ----
FUNC_LABEL = {
    "serial_cdev": "MODEM",   # 진짜 모뎀/AT (구 표시명 "DM")
    "diag": "DIAG",           # Qualcomm DIAG (구 표시명 "MODEM")
    "rmnet": "RMNET",
    "dpl": "ADPL",
    "qdss": "QDSS",
    "adb": "ADB",
    "acm": "MODEM(acm)",      # Samsung REF
    "rndis": "RNDIS",
    "mtp": "MTP",
    "ptp": "PTP",
}

RELEVANT_PROPS = (
    "persist.sys.usb.config",
    "sys.usb.config",
    "sys.usb.qmmi.func",
    "persist.sys.usb.qmmi.func",
    "ro.build.version.incremental",
    "ro.build.display_build_number",            # = AT-M150Z0624U
    "ro.build.display_build_number_internal",   # = ..Z0624U_DAILY_DEV_GMS_570
    "gsm.sim.operator.alpha",
    "gsm.operator.alpha",
    "ro.product.model",
)


def _qmmi(props: dict) -> str | None:
    """qmmi 기본 composition prop — ODIN2 는 persist.sys.usb.qmmi.func."""
    return props.get("persist.sys.usb.qmmi.func") or props.get("sys.usb.qmmi.func")

# 부팅 후 복원체인 증거 (reference_usb_composition_test.md)
RESTORE_PATTERNS = (
    r"getPersistProp:\s*return=persist\.sys\.usb",
    r"persist\.sys\.usb\.config=\*\s*&&\s*boot",
    r"setEnabledFunctions:\s*usbFunctions=",
)
# 기본값 복귀(FAIL) 알림
REVERT_PATTERNS = (
    r"UsbDeviceManager:\s*push notification:",
)


# =========================================================================
# 순수 함수 (selftest 대상 — 단말 불필요)
# =========================================================================
def parse_getprop(text: str) -> dict:
    """`getprop` 전체 출력(`[key]: [value]`)에서 관심 prop 만 추출."""
    out = {}
    for m in re.finditer(r"\[([^\]]+)\]:\s*\[([^\]]*)\]", text):
        k, v = m.group(1), m.group(2)
        if k in RELEVANT_PROPS:
            out[k] = v
    return out


def normalize_funcs(value: str | None) -> tuple:
    """composition func string -> 정규화 set(순서 무관, 공백/빈값 제거)."""
    if not value:
        return tuple()
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return tuple(sorted(set(parts)))


def func_to_labels(funcs) -> list:
    if isinstance(funcs, str):
        funcs = normalize_funcs(funcs)
    return [FUNC_LABEL.get(f, f) for f in funcs]


def parse_uiauto_selected(xml: str) -> dict:
    """uiautomator dump 에서 선택 라벨 / summary(<label>:<func>) 추출."""
    res = {"checked_texts": [], "summaries": []}
    # checked="true" 노드의 text
    for m in re.finditer(r'<node[^>]*\bchecked="true"[^>]*\btext="([^"]+)"', xml):
        if m.group(1).strip():
            res["checked_texts"].append(m.group(1).strip())
    # summary 패턴 "ADB:adb" / "DIAG + MODEM:diag,serial_cdev" 등
    for m in re.finditer(r'\btext="([^"]+:[^"]+)"', xml):
        t = m.group(1).strip()
        if re.search(r":[a-z_,]+$", t):
            res["summaries"].append(t)
    return res


def parse_data_state(dumpsys_text: str = "", ip_text: str = "", ping_text: str = "") -> dict:
    """composition별 데이터 무결성 신호 (TC-06)."""
    connected = None
    m = re.search(r"mDataConnectionState\s*=\s*(\d)", dumpsys_text) \
        or re.search(r"DataConnectionState\s*[:=]\s*(\d)", dumpsys_text)
    if m:
        connected = (m.group(1) == "2")  # 2 = CONNECTED
    has_ip = bool(re.search(r"rmnet_data\d+.*?inet\s+\d", ip_text, re.S)) \
        or bool(re.search(r"inet\s+\d+\.\d+\.\d+\.\d+.*rmnet_data", ip_text))
    reachable = None
    if ping_text:
        if re.search(r"0% packet loss", ping_text):
            reachable = True
        elif re.search(r"100% packet loss|unreachable|bad address", ping_text):
            reachable = False
    return {
        "data_connected": connected,
        "rmnet_has_ip": has_ip,
        "ping_reachable": reachable,
        "data_ok": bool(connected) and has_ip and (reachable in (True, None)),
    }


def find_restore_chain(logcat_text: str) -> dict:
    seen = [p for p in RESTORE_PATTERNS if re.search(p, logcat_text)]
    revert = [p for p in REVERT_PATTERNS if re.search(p, logcat_text)]
    return {"restore_seen": bool(seen), "matched": seen, "revert_notice": bool(revert)}


def judge_retention(post_props: dict, expected: str, qmmi_default: str | None = None,
                    restore_seen: bool | None = None) -> dict:
    """재부팅 후 유지 판정. PASS = W2 & W3-active & (복원체인 or 미입력)."""
    exp = normalize_funcs(expected)
    persist = normalize_funcs(post_props.get("persist.sys.usb.config"))
    active = normalize_funcs(post_props.get("sys.usb.config"))
    qmmi = normalize_funcs(qmmi_default or _qmmi(post_props))

    w2_persist_ok = persist == exp and len(exp) > 0
    w3_active_ok = active == exp and len(exp) > 0

    reasons = []
    # FAIL 시그니처 (4월 회귀)
    truncated = bool(persist) and persist != exp and set(persist).issubset(set(exp))
    qmmi_revert = bool(qmmi) and active == qmmi and active != exp
    if truncated:
        reasons.append(f"persist 절단: persist={','.join(persist)} ⊂ expected={','.join(exp)}")
    if qmmi_revert:
        reasons.append(f"qmmi 기본 복귀: sys.usb.config==sys.usb.qmmi.func({','.join(qmmi)})")
    if not w2_persist_ok and not truncated:
        reasons.append(f"W2 persist 불일치: {','.join(persist) or '(empty)'} != {','.join(exp)}")
    if not w3_active_ok and not qmmi_revert:
        reasons.append(f"W3 active 불일치: {','.join(active) or '(empty)'} != {','.join(exp)}")
    if restore_seen is False:
        reasons.append("복원체인 미관찰 (getPersistProp / persist..config=*&&boot / setEnabledFunctions)")

    verdict = "PASS" if (w2_persist_ok and w3_active_ok and restore_seen in (True, None)
                         and not truncated and not qmmi_revert) else "FAIL"
    return {
        "verdict": verdict,
        "expected": list(exp),
        "persist": list(persist),
        "active": list(active),
        "qmmi_default": list(qmmi),
        "W2_persist_ok": w2_persist_ok,
        "W3_active_ok": w3_active_ok,
        "restore_seen": restore_seen,
        "reasons": reasons,
    }


# =========================================================================
# adb 헬퍼 — read-only 화이트리스트만 허용
# =========================================================================
_READONLY_OK = ("getprop", "dumpsys", "uiautomator", "ip", "ping", "cat", "logcat")


def _adb(serial: str, *args: str, timeout: int = 30) -> str:
    if args and args[0] == "shell" and len(args) > 1:
        head = args[1].split()[0] if isinstance(args[1], str) else args[1]
        if head not in _READONLY_OK:
            raise SystemExit(f"REFUSED non-readonly shell cmd: {head}")
    cmd = ["adb", "-s", serial, *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception as e:  # noqa: BLE001
        return f"(adb error: {e})"


def _resolve_serial(args) -> str:
    s = getattr(args, "serial", None) or os.environ.get("USB_DEV")
    if not s:
        raise SystemExit("serial 미지정 — --serial <id> 또는 env USB_DEV 필요 (wrong-device 가드)")
    devs = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    attached = [ln.split()[0] for ln in devs.splitlines()[1:] if "\tdevice" in ln]
    if attached and s not in attached:
        raise SystemExit(f"WRONG DEVICE: '{s}' 미연결. 연결됨={attached}")
    return s


# =========================================================================
# 서브커맨드
# =========================================================================
def cmd_preflight(args):
    s = _resolve_serial(args)
    props = parse_getprop(_adb(s, "shell", "getprop"))
    build = (props.get("ro.build.display_build_number_internal")
             or props.get("ro.build.display_build_number")
             or props.get("ro.build.version.incremental", "?"))
    carrier = props.get("gsm.sim.operator.alpha") or props.get("gsm.operator.alpha", "?")
    model = props.get("ro.product.model", "?")
    print(f"serial={s} model={model} build={build} carrier={carrier}")
    print(f"  sys.usb.config      = {props.get('sys.usb.config','?')}")
    print(f"  persist.sys.usb.cfg = {props.get('persist.sys.usb.config','?')}")
    print(f"  qmmi.func(persist)  = {_qmmi(props) or '?'}")
    if args.expect_build and args.expect_build not in build:
        print(f"  ⚠ 빌드 기대 '{args.expect_build}' 불일치 → 중단 권장")
    if args.expect_carrier and args.expect_carrier.upper() not in (carrier or "").upper():
        print(f"  ⚠ carrier 기대 '{args.expect_carrier}' 불일치 → SIM 확인")
    return 0


def cmd_snapshot(args):
    s = _resolve_serial(args)
    label = args.label
    props = parse_getprop(_adb(s, "shell", "getprop"))
    # device-lost 가드: getprop 이 핵심 키를 못 주면 USB 끊김 → junk snapshot 방지
    if "sys.usb.config" not in props:
        raise SystemExit(f"DEVICE LOST: '{s}' getprop 무응답 (USB 끊김?). "
                         f"adb devices 재확인 후 재시도 — snapshot 미기록")
    outdir = os.path.join(args.evidence, label)
    os.makedirs(outdir, exist_ok=True)
    # uiautomator dump (read-only)
    _adb(s, "shell", "uiautomator dump /sdcard/_usbdump.xml")
    ui_xml = _adb(s, "shell", "cat /sdcard/_usbdump.xml")
    ui = parse_uiauto_selected(ui_xml)
    data = parse_data_state(
        _adb(s, "shell", "dumpsys telephony.registry"),
        _adb(s, "shell", "ip -o addr"),
        _adb(s, "shell", "ping -c 3 -W 2 8.8.8.8"),
    )
    snap = {"label": label, "serial": s, "props": props,
            "ui": ui, "data": data,
            "active_labels": func_to_labels(props.get("sys.usb.config", "")),
            "persist_labels": func_to_labels(props.get("persist.sys.usb.config", ""))}
    with open(os.path.join(outdir, "snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    print(f"[{label}] sys={props.get('sys.usb.config','?')} | "
          f"persist={props.get('persist.sys.usb.config','?')} | "
          f"data_ok={data['data_ok']} -> {outdir}/snapshot.json")
    return 0


def cmd_judge(args):
    with open(args.post, encoding="utf-8") as f:
        post = json.load(f)
    logcat_text = ""
    if args.logcat and os.path.exists(args.logcat):
        with open(args.logcat, encoding="utf-8", errors="ignore") as f:
            logcat_text = f.read()
    restore = find_restore_chain(logcat_text)["restore_seen"] if logcat_text else None
    r = judge_retention(post["props"], args.expect, restore_seen=restore)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["verdict"] == "PASS" else 2


def cmd_ports(args):
    if sys.platform != "win32":
        print("(ports: Windows 전용 — Get-PnpDevice)")
        return 0
    # 실제 폰 USB 인터페이스만: InstanceId 가 USB\ (물리연결) + 폰 포트 패턴/Class.
    # 호스트 잡음(ROOT/SWD/SW 가상 Net·Intel Serial IO·"Component"의 COM 등)과
    # 비-폰 USB(ASIX dongle·Hub·Host Controller) 제외.
    ps = (
        r"Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\*' } | "
        r"Where-Object { "
        r"( $_.FriendlyName -match '\(COM\d+\)|Qualcomm|HS-USB|Diagnostics|NMEA|Android|ADB|RNDIS|\bMTP\b|\bPTP\b|AT-M150|Marvell' ) -or "
        r"( $_.Class -in @('Ports','Modem','WPD','AndroidUsbDeviceClass') ) "
        r"} | Where-Object { $_.FriendlyName -notmatch 'ASIX|Hub|Host Controller' } | "
        r"Select-Object Status,Class,FriendlyName,InstanceId | Format-Table -Wrap | Out-String")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True).stdout
    print(out or "(no matching USB ports)")
    return 0


def cmd_selftest(args):
    # --- parse_getprop / normalize ---
    gp = "[persist.sys.usb.config]: [adb]\n[sys.usb.config]: [diag,serial_cdev,rmnet,dpl,qdss,adb]\n[sys.usb.qmmi.func]: [diag,serial_cdev,rmnet,dpl,qdss,adb]\n"
    p = parse_getprop(gp)
    assert p["persist.sys.usb.config"] == "adb"
    assert normalize_funcs("adb,diag, adb ") == ("adb", "diag")
    assert func_to_labels("serial_cdev,diag") == ["DIAG", "MODEM"]  # 정렬: diag,serial_cdev

    # --- FAIL 시그니처(4월 회귀): idx10 선택했으나 persist 절단 + qmmi(idx12) 복귀 ---
    # p: persist=adb(절단), sys.usb.config=qmmi=idx12 full(복귀). expected=idx10(실제 선택).
    fail = judge_retention(p, "diag,adb,serial_cdev")
    assert fail["verdict"] == "FAIL", fail
    assert any("절단" in r for r in fail["reasons"]), fail
    assert any("qmmi 기본 복귀" in r for r in fail["reasons"]), fail

    # --- PASS 시그니처(수정됨) ---
    good = {"persist.sys.usb.config": "diag,serial_cdev,rmnet,dpl,qdss,adb",
            "sys.usb.config": "diag,serial_cdev,rmnet,dpl,qdss,adb",
            "sys.usb.qmmi.func": "diag,serial_cdev,rmnet,dpl,qdss,adb"}
    ok = judge_retention(good, "diag,adb,serial_cdev,rmnet,dpl,qdss", restore_seen=True)
    assert ok["verdict"] == "PASS", ok

    # restore 미관찰 시 FAIL
    no_restore = judge_retention(good, "diag,serial_cdev,rmnet,dpl,qdss,adb", restore_seen=False)
    assert no_restore["verdict"] == "FAIL", no_restore

    # --- uiautomator 선택 라벨 / summary ---
    xml = '<node checked="true" text="DIAG + MODEM + ADB"/><node text="USB:diag,adb,serial_cdev"/>'
    ui = parse_uiauto_selected(xml)
    assert ui["checked_texts"] == ["DIAG + MODEM + ADB"], ui
    assert ui["summaries"] == ["USB:diag,adb,serial_cdev"], ui

    # --- 복원체인 / 데이터 ---
    lc = "getPersistProp: return=persist.sys.usb.q_config\nsetEnabledFunctions: usbFunctions=diag,adb\n"
    assert find_restore_chain(lc)["restore_seen"] is True
    d = parse_data_state("mDataConnectionState=2",
                         "12: rmnet_data0    inet 10.1.2.3/30",
                         "3 packets transmitted, 3 received, 0% packet loss")
    assert d["data_ok"] is True, d
    d2 = parse_data_state("mDataConnectionState=0", "", "100% packet loss")
    assert d2["data_ok"] is False, d2

    print("selftest OK — 모든 순수 함수 검증 통과")
    return 0


def main():
    ap = argparse.ArgumentParser(description="USB composition 유지 검증 (read-only)")
    ap.add_argument("--serial", help="adb serial (또는 env USB_DEV)")
    ap.add_argument("--evidence", default=os.path.join(
        "ODIN2 - USB Composition BTS25462", "evidence"), help="증거 출력 디렉토리")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("preflight"); pf.set_defaults(func=cmd_preflight)
    pf.add_argument("--expect-build", default="Z0623U")
    pf.add_argument("--expect-carrier", default="SKT")

    sn = sub.add_parser("snapshot"); sn.add_argument("label"); sn.set_defaults(func=cmd_snapshot)

    jd = sub.add_parser("judge"); jd.set_defaults(func=cmd_judge)
    jd.add_argument("post", help="post-reboot snapshot.json")
    jd.add_argument("--expect", required=True, help="선택 조합 func string")
    jd.add_argument("--logcat", help="boot-crossing logcat 텍스트(복원체인 확인)")

    sub.add_parser("ports").set_defaults(func=cmd_ports)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
