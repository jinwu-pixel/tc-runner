"""PR 3 Screen Identity Catalog.

preflight manifest를 입력으로 받아 화면 단위 누적 데이터를
<app_dir>/catalog/screens.json + visits.jsonl 에 기록한다.
append-only visits log + screen identity registry 패턴.

manifest_path 정책
------------------
- 입력 문자열을 그대로 저장한다. path normalization은 하지 않는다.
- 같은 파일이라도 다른 경로 문자열로 입력하면 별도 visit으로 처리된다.
- normalization은 PR 4 후보다.

idempotency key
---------------
- (manifest_path 문자열, manifest["run_id"] 문자열)
- 동일 key 재실행은 full skip — visits append 0, screens.observed_count 증가 0,
  visible_texts union 미수행, screens.json rewrite 없음.

run_id
------
- manifest["run_id"] 만 source of truth.
- CLI override run_id 옵션은 존재하지 않는다.

identity
--------
- screen_id = sha256(f"{current_activity or 'UNKNOWN_ACTIVITY'}\\n{xml_sha256}")
- xml_sha256 가 없는 manifest는 skip한다.
- screenshot_sha256은 secondary metadata이며 identity 계산에 사용하지 않는다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
TOOL_VERSION = "pr3-catalog-v1"

DEFAULT_FROM_REPORTS = Path("reports/preflight")

SCREEN_KIND_TARGET = "target_app"
SCREEN_KIND_LOCKSCREEN = "lockscreen_or_non_target"
SCREEN_KIND_OTHER = "other_app_or_system"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def compute_screen_id(current_activity: str | None, xml_sha256: str | None) -> str | None:
    """xml_sha256가 없으면 None. current_activity null은 'UNKNOWN_ACTIVITY'로 치환."""
    if not isinstance(xml_sha256, str) or not xml_sha256:
        return None
    activity = current_activity if isinstance(current_activity, str) and current_activity else "UNKNOWN_ACTIVITY"
    payload = f"{activity}\n{xml_sha256}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def classify_screen_kind(manifest: dict, target_package: str | None) -> str:
    """current_activity와 target_package로 screen_kind를 판정.

    - current_activity null 또는 preflight_status.reasons에 activity_parse_failed →
      lockscreen_or_non_target
    - target_package 가 set 이고 current_activity 가 target_package prefix 로 시작 →
      target_app
    - 그 외 → other_app_or_system
    """
    screen = manifest.get("screen") or {}
    current_activity = screen.get("current_activity")

    preflight_status = manifest.get("preflight_status") or {}
    reasons = preflight_status.get("reasons") or []

    if not isinstance(current_activity, str) or not current_activity:
        return SCREEN_KIND_LOCKSCREEN
    if isinstance(reasons, list) and "activity_parse_failed" in reasons:
        return SCREEN_KIND_LOCKSCREEN

    if isinstance(target_package, str) and target_package.strip():
        prefix = target_package.strip()
        if current_activity.startswith(f"{prefix}/") or current_activity.startswith(f"{prefix}."):
            return SCREEN_KIND_TARGET

    return SCREEN_KIND_OTHER


def union_visible_texts(existing: list[str], new: list[str]) -> list[str]:
    """기존 + 신규 합집합. 순서 보존, 중복 제거. cap 없음."""
    seen: set[str] = set()
    result: list[str] = []
    for text in list(existing) + list(new):
        if not isinstance(text, str):
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def discover_manifests(from_reports_dir: Path) -> list[Path]:
    """from_reports_dir 하위 manifest.json을 모두 찾아 정렬된 리스트로 반환."""
    if not isinstance(from_reports_dir, Path):
        from_reports_dir = Path(from_reports_dir)
    if not from_reports_dir.is_dir():
        return []
    return sorted(from_reports_dir.rglob("manifest.json"))


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _load_manifest(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _empty_screens_doc(app_dir: Path, target_package: str | None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "app_dir": app_dir.name,
        "target_package": target_package,
        "generated_at": _now_iso(),
        "screens": {},
    }


def _load_screens_doc(catalog_dir: Path, app_dir: Path, target_package: str | None) -> dict:
    path = catalog_dir / "screens.json"
    if not path.exists():
        return _empty_screens_doc(app_dir, target_package)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return _empty_screens_doc(app_dir, target_package)
    if not isinstance(data, dict):
        return _empty_screens_doc(app_dir, target_package)
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("tool_version", TOOL_VERSION)
    data.setdefault("app_dir", app_dir.name)
    if "screens" not in data or not isinstance(data["screens"], dict):
        data["screens"] = {}
    return data


def _load_visits_keys(catalog_dir: Path) -> set[tuple[str, str]]:
    path = catalog_dir / "visits.jsonl"
    if not path.exists():
        return set()
    keys: set[tuple[str, str]] = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    visit = json.loads(line)
                except json.JSONDecodeError:
                    continue
                mp = visit.get("manifest_path")
                rid = visit.get("run_id")
                if isinstance(mp, str) and isinstance(rid, str):
                    keys.add((mp, rid))
    except OSError:
        pass
    return keys


def _append_visit(catalog_dir: Path, visit: dict) -> None:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    path = catalog_dir / "visits.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(visit, ensure_ascii=False) + "\n")


def _write_screens(catalog_dir: Path, doc: dict) -> None:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    path = catalog_dir / "screens.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def _resolve_target_package(
    explicit: str | None,
    loaded: list[tuple[str, dict]],
) -> tuple[str | None, bool]:
    """target_package 결정 + mixed_warning.

    explicit 우선. 없으면 sorted manifests 순회 중 첫 valid app.package_name.
    여러 unique package_name 발견 시 mixed_warning=True (PR 4 후속).
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for _, manifest in loaded:
        app = manifest.get("app") or {}
        pkg = app.get("package_name")
        if isinstance(pkg, str) and pkg.strip():
            normalized = pkg.strip()
            if normalized not in seen_set:
                seen_set.add(normalized)
                seen.append(normalized)

    mixed = len(seen_set) > 1

    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip(), mixed

    return (seen[0] if seen else None), mixed


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_build(
    app_dir: Path,
    *,
    from_reports: Path | None = None,
    manifest: Path | None = None,
    target_package: str | None = None,
) -> dict[str, Any]:
    """catalog build 진입점.

    from_reports와 manifest 동시 지정 시 ValueError.
    둘 다 None이면 from_reports = DEFAULT_FROM_REPORTS.
    """
    if from_reports is not None and manifest is not None:
        raise ValueError("--from-reports 와 --manifest 는 동시 지정할 수 없습니다")

    if not isinstance(app_dir, Path):
        app_dir = Path(app_dir)

    if manifest is not None:
        manifest_input_paths = [manifest if isinstance(manifest, Path) else Path(manifest)]
    else:
        from_reports_dir = from_reports if from_reports is not None else DEFAULT_FROM_REPORTS
        if not isinstance(from_reports_dir, Path):
            from_reports_dir = Path(from_reports_dir)
        manifest_input_paths = discover_manifests(from_reports_dir)

    summary: dict[str, Any] = {
        "discovered": len(manifest_input_paths),
        "added": 0,
        "updated": 0,
        "skipped_duplicate": 0,
        "skipped_missing_run_id": 0,
        "skipped_no_xml_hash": 0,
        "skipped_invalid_json": 0,
        "mixed_package_warning": False,
        "target_package": None,
    }

    loaded: list[tuple[str, dict]] = []
    invalid_count = 0
    for path in manifest_input_paths:
        path_str = str(path)
        m = _load_manifest(path)
        if m is None:
            invalid_count += 1
            continue
        loaded.append((path_str, m))

    summary["skipped_invalid_json"] = invalid_count

    resolved_target, mixed = _resolve_target_package(target_package, loaded)
    summary["target_package"] = resolved_target
    summary["mixed_package_warning"] = mixed

    catalog_dir = app_dir / "catalog"
    screens_doc = _load_screens_doc(catalog_dir, app_dir, resolved_target)

    initial_target = screens_doc.get("target_package")
    initial_app_dir = screens_doc.get("app_dir")

    screens_doc["target_package"] = resolved_target
    screens_doc["app_dir"] = app_dir.name

    visits_keys = _load_visits_keys(catalog_dir)

    dirty = (
        screens_doc["target_package"] != initial_target
        or screens_doc["app_dir"] != initial_app_dir
    )

    for path_str, m in loaded:
        run_id_raw = m.get("run_id")
        if not isinstance(run_id_raw, str) or not run_id_raw.strip():
            summary["skipped_missing_run_id"] += 1
            continue
        run_id = run_id_raw.strip()

        screen = m.get("screen") or {}
        xml_sha256 = screen.get("xml_sha256")
        if not isinstance(xml_sha256, str) or not xml_sha256:
            summary["skipped_no_xml_hash"] += 1
            continue

        key = (path_str, run_id)
        if key in visits_keys:
            summary["skipped_duplicate"] += 1
            continue

        current_activity = screen.get("current_activity")
        screen_id = compute_screen_id(current_activity, xml_sha256)
        if screen_id is None:
            summary["skipped_no_xml_hash"] += 1
            continue

        kind = classify_screen_kind(m, resolved_target)

        text_model = m.get("text_model") or {}
        new_texts_raw = text_model.get("visible_texts_from_dump") or []
        new_texts = [t for t in new_texts_raw if isinstance(t, str)]

        screenshot_sha256 = screen.get("screenshot_sha256")
        if not isinstance(screenshot_sha256, str):
            screenshot_sha256 = None

        now = _now_iso()
        screens = screens_doc["screens"]

        if screen_id not in screens:
            screens[screen_id] = {
                "screen_id": screen_id,
                "screen_kind": kind,
                "current_activity": current_activity if isinstance(current_activity, str) else None,
                "xml_sha256": xml_sha256,
                "observed_count": 1,
                "first_seen": now,
                "last_seen": now,
                "visible_texts": list(new_texts),
            }
            summary["added"] += 1
            dirty = True
        else:
            entry = screens[screen_id]
            entry["observed_count"] = entry.get("observed_count", 0) + 1
            entry["last_seen"] = now
            old_texts = entry.get("visible_texts") or []
            if not isinstance(old_texts, list):
                old_texts = []
            merged = union_visible_texts(old_texts, new_texts)
            entry["visible_texts"] = merged
            summary["updated"] += 1
            dirty = True

        visit = {
            "observed_at": now,
            "manifest_path": path_str,
            "run_id": run_id,
            "screen_id": screen_id,
            "screen_kind": kind,
            "screenshot_sha256": screenshot_sha256,
        }
        _append_visit(catalog_dir, visit)
        visits_keys.add(key)

    if dirty:
        screens_doc["generated_at"] = _now_iso()
        _write_screens(catalog_dir, screens_doc)

    return summary


def cmd_show(app_dir: Path) -> str:
    """screens.json 요약을 다단 텍스트로 반환."""
    if not isinstance(app_dir, Path):
        app_dir = Path(app_dir)
    path = app_dir / "catalog" / "screens.json"
    if not path.exists():
        raise FileNotFoundError(f"screens.json 가 없습니다: {path}")

    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    screens = doc.get("screens") or {}
    counts = {
        SCREEN_KIND_TARGET: 0,
        SCREEN_KIND_LOCKSCREEN: 0,
        SCREEN_KIND_OTHER: 0,
    }
    rows: list[tuple[str, str, str, int, str]] = []
    for sid, entry in screens.items():
        kind = entry.get("screen_kind", "?")
        if kind in counts:
            counts[kind] += 1
        rows.append((
            sid[:12],
            kind,
            entry.get("current_activity") or "—",
            int(entry.get("observed_count", 0) or 0),
            entry.get("last_seen") or "—",
        ))

    lines: list[str] = []
    lines.append(f"app_dir: {doc.get('app_dir')}")
    lines.append(f"target_package: {doc.get('target_package')}")
    lines.append(f"generated_at: {doc.get('generated_at')}")
    lines.append("")
    lines.append(f"  total: {len(screens)}")
    lines.append(f"  target_app: {counts[SCREEN_KIND_TARGET]}")
    lines.append(f"  lockscreen_or_non_target: {counts[SCREEN_KIND_LOCKSCREEN]}")
    lines.append(f"  other_app_or_system: {counts[SCREEN_KIND_OTHER]}")
    if rows:
        lines.append("")
        lines.append(
            f"{'screen_id':12s}  {'kind':25s}  {'observed':>8s}  {'last_seen':20s}  current_activity"
        )
        for sid12, kind, activity, observed, last_seen in rows:
            lines.append(
                f"{sid12:12s}  {kind:25s}  {observed:>8d}  {last_seen:20s}  {activity}"
            )
    return "\n".join(lines)
