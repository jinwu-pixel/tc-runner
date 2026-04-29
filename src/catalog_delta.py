"""PR 4 Catalog Delta Detector.

읽기 전용. catalog mutation 절대 금지.
preflight manifest 한 건과 catalog screens.json 을 비교하여
delta verdict + interpretation flags 를 reports/catalog_delta/<run_id>.json 에 기록한다.

verdict priority (rev2 + 최종 결정):
1. insufficient
2. non_target_context
3. known_screen
4. changed_texts
5. new_screen

interpretation_flags 는 verdict 를 뒤집지 않는다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.catalog import classify_screen_kind, compute_screen_id

SCHEMA_VERSION = 1
TOOL_VERSION = "pr4-delta-v1"
DEFAULT_OUTPUT_DIR = Path("reports/catalog_delta")
DEFAULT_JACCARD_THRESHOLD = 0.5

VERDICT_INSUFFICIENT = "insufficient"
VERDICT_NON_TARGET_CONTEXT = "non_target_context"
VERDICT_KNOWN_SCREEN = "known_screen"
VERDICT_CHANGED_TEXTS = "changed_texts"
VERDICT_NEW_SCREEN = "new_screen"

# 파일명으로 위험한 문자 (rev2 최종 결정 1)
INVALID_RUN_ID_CHARS = set('/\\:*?"<>|')


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def validate_run_id_for_filename(run_id: Any) -> str:
    """run_id 가 출력 파일명으로 안전한지 검증. 부적합 시 ValueError."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id 가 비어있거나 문자열이 아닙니다")
    rid = run_id.strip()
    bad = sorted({ch for ch in rid if ch in INVALID_RUN_ID_CHARS})
    if bad:
        raise ValueError(
            f"run_id 에 파일명 위험 문자가 포함되어 있습니다: {''.join(bad)}"
        )
    return rid


def jaccard_texts(a: list[str], b: list[str]) -> float | None:
    """두 텍스트 집합의 Jaccard 유사도. 둘 다 비어있으면 None, 한쪽만 비면 0.0."""
    sa = {t for t in (a or []) if isinstance(t, str)}
    sb = {t for t in (b or []) if isinstance(t, str)}
    if not sa and not sb:
        return None
    if not sa or not sb:
        return 0.0
    intersection = len(sa & sb)
    union = len(sa | sb)
    return intersection / union


def diff_texts(
    baseline: list[str], current: list[str]
) -> tuple[list[str], list[str]]:
    """baseline=catalog, current=manifest 기준.

    added_texts = manifest ∖ catalog
    removed_texts = catalog ∖ manifest
    각각 정렬된 리스트.
    """
    sb = {t for t in (baseline or []) if isinstance(t, str)}
    sc = {t for t in (current or []) if isinstance(t, str)}
    added = sorted(sc - sb)
    removed = sorted(sb - sc)
    return added, removed


def load_catalog(catalog_dir: Path) -> dict:
    """catalog screens.json 을 읽어 dict 반환.

    파일이 없으면 빈 catalog 를 반환하여 evaluate_delta 에서 insufficient 처리되게 한다.
    catalog_dir 자체가 없으면 FileNotFoundError.
    """
    if not isinstance(catalog_dir, Path):
        catalog_dir = Path(catalog_dir)
    if not catalog_dir.is_dir():
        raise FileNotFoundError(f"catalog 디렉토리가 없습니다: {catalog_dir}")
    path = catalog_dir / "screens.json"
    if not path.is_file():
        return {"target_package": None, "screens": {}}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"catalog screens.json 가 dict 가 아닙니다: {path}")
    return data


def load_manifest(path: Path) -> dict:
    """preflight manifest.json 을 읽어 dict 반환."""
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"manifest 가 없습니다: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"manifest 가 dict 가 아닙니다: {path}")
    return data


# ---------------------------------------------------------------------------
# evaluate_delta
# ---------------------------------------------------------------------------


def _str_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def evaluate_delta(
    manifest: dict,
    catalog_doc: dict,
    *,
    manifest_path: str,
    catalog_dir: str,
    threshold: float,
) -> dict:
    """단일 manifest 와 catalog_doc 간 delta 평가. report dict 반환."""
    # ---- manifest 추출 ----
    app = manifest.get("app") or {}
    manifest_pkg_raw = app.get("package_name") if isinstance(app, dict) else None
    manifest_pkg = _str_or_none(manifest_pkg_raw)

    screen = manifest.get("screen") or {}
    if not isinstance(screen, dict):
        screen = {}
    current_activity = _str_or_none(screen.get("current_activity"))
    xml_sha256 = _str_or_none(screen.get("xml_sha256"))

    text_model = manifest.get("text_model") or {}
    if not isinstance(text_model, dict):
        text_model = {}
    visible_texts_raw = text_model.get("visible_texts_from_dump") or []
    if not isinstance(visible_texts_raw, list):
        visible_texts_raw = []
    visible_texts = [t for t in visible_texts_raw if isinstance(t, str)]

    preflight_status = manifest.get("preflight_status") or {}
    if not isinstance(preflight_status, dict):
        preflight_status = {}
    pf_level = _str_or_none(preflight_status.get("level"))
    pf_reasons_raw = preflight_status.get("reasons") or []
    pf_reasons = (
        [r for r in pf_reasons_raw if isinstance(r, str)]
        if isinstance(pf_reasons_raw, list)
        else []
    )

    # ---- catalog 추출 ----
    catalog_target_pkg = _str_or_none(catalog_doc.get("target_package"))
    catalog_screens = catalog_doc.get("screens") or {}
    if not isinstance(catalog_screens, dict):
        catalog_screens = {}

    package_match = (
        manifest_pkg is not None
        and catalog_target_pkg is not None
        and manifest_pkg == catalog_target_pkg
    )
    package_mismatch = (
        manifest_pkg is not None
        and catalog_target_pkg is not None
        and manifest_pkg != catalog_target_pkg
    )

    # ---- manifest_kind ----
    manifest_kind = classify_screen_kind(manifest, catalog_target_pkg)

    # ---- screen_id ----
    screen_id = compute_screen_id(current_activity, xml_sha256)

    # ---- interpretation flags (verdict 와 무관하게 항상 계산) ----
    flags: list[str] = []
    if "expected_texts_missing" in pf_reasons and manifest_kind == "target_app":
        flags.append("preset_unknown")
    if manifest_kind == "lockscreen_or_non_target":
        flags.append("lockscreen_context")
    if manifest_kind == "other_app_or_system":
        flags.append("non_target_app_context")
    if package_mismatch:
        flags.append("cross_app_context")

    # ---- insufficient_reasons ----
    insufficient_reasons: list[str] = []
    if xml_sha256 is None:
        insufficient_reasons.append("xml_sha256_missing")
    if manifest_pkg is None:
        insufficient_reasons.append("manifest_package_missing")
    if catalog_target_pkg is None:
        insufficient_reasons.append("catalog_target_package_missing")
    if package_mismatch:
        insufficient_reasons.append("package_mismatch")
    if current_activity is None and not visible_texts:
        insufficient_reasons.append("current_activity_and_visible_texts_missing")
    if not catalog_screens:
        insufficient_reasons.append("catalog_screens_empty")

    # ---- delta 결정 ----
    delta: dict[str, Any] = {
        "verdict": "",
        "baseline_screen_id": None,
        "jaccard": None,
        "added_texts": None,
        "removed_texts": None,
    }

    if insufficient_reasons:
        delta["verdict"] = VERDICT_INSUFFICIENT
    elif manifest_kind != "target_app":
        delta["verdict"] = VERDICT_NON_TARGET_CONTEXT
    elif screen_id is not None and screen_id in catalog_screens:
        delta["verdict"] = VERDICT_KNOWN_SCREEN
        delta["baseline_screen_id"] = screen_id
    else:
        # 동일 current_activity catalog 후보 수집
        candidates: list[tuple[float, str, list[str]]] = []
        for sid, entry in catalog_screens.items():
            if not isinstance(entry, dict):
                continue
            entry_activity = entry.get("current_activity")
            if entry_activity != current_activity:
                continue
            entry_texts_raw = entry.get("visible_texts") or []
            entry_texts = (
                [t for t in entry_texts_raw if isinstance(t, str)]
                if isinstance(entry_texts_raw, list)
                else []
            )
            j = jaccard_texts(entry_texts, visible_texts)
            if j is None:
                # 양쪽 모두 비어있는 경우 — 후보에서 제외
                continue
            candidates.append((j, sid, entry_texts))

        if candidates:
            # tie-break: highest J first, then lex-smallest screen_id
            candidates.sort(key=lambda x: (-x[0], x[1]))
            best_j, best_sid, best_texts = candidates[0]
            if best_j >= threshold:
                delta["verdict"] = VERDICT_CHANGED_TEXTS
                delta["baseline_screen_id"] = best_sid
                delta["jaccard"] = best_j
                added, removed = diff_texts(best_texts, visible_texts)
                delta["added_texts"] = added
                delta["removed_texts"] = removed
            else:
                delta["verdict"] = VERDICT_NEW_SCREEN
        else:
            delta["verdict"] = VERDICT_NEW_SCREEN

    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "run_id": manifest.get("run_id") if isinstance(manifest.get("run_id"), str) else None,
        "generated_at": _now_iso(),
        "catalog_dir": catalog_dir,
        "catalog_target_package": catalog_target_pkg,
        "manifest_path": manifest_path,
        "manifest_target_package": manifest_pkg,
        "package_match": package_match,
        "manifest_kind": manifest_kind,
        "jaccard_threshold": threshold,
        "screen": {
            "screen_id": screen_id,
            "current_activity": current_activity,
            "xml_sha256": xml_sha256,
            "visible_texts": visible_texts,
        },
        "delta": delta,
        "preflight_status": {
            "level": pf_level,
            "reasons": pf_reasons,
        },
        "interpretation_flags": flags,
        "insufficient_reasons": insufficient_reasons,
    }


# ---------------------------------------------------------------------------
# cmd_delta
# ---------------------------------------------------------------------------


def cmd_delta(
    catalog_dir: Path,
    manifest: Path,
    *,
    output_dir: Path | None = None,
    threshold: float = DEFAULT_JACCARD_THRESHOLD,
) -> dict:
    """delta detector 진입점. report 작성 + dict 반환.

    run_id 검증 실패 시 ValueError raise (caller 가 stderr+exit 처리).
    threshold 범위 위반 시 ValueError.
    catalog_dir / manifest 미존재 시 FileNotFoundError.
    catalog screens.json 무효 JSON 시 ValueError (insufficient 아님 — 데이터 손상).
    """
    if not isinstance(catalog_dir, Path):
        catalog_dir = Path(catalog_dir)
    if not isinstance(manifest, Path):
        manifest = Path(manifest)
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    if not isinstance(output_dir, Path):
        output_dir = Path(output_dir)

    if not (0.0 <= threshold <= 1.0):
        raise ValueError(
            f"jaccard threshold 는 0.0 ~ 1.0 범위여야 합니다: {threshold}"
        )

    catalog_doc = load_catalog(catalog_dir)
    manifest_doc = load_manifest(manifest)

    run_id_raw = manifest_doc.get("run_id")
    run_id = validate_run_id_for_filename(run_id_raw)

    report = evaluate_delta(
        manifest_doc,
        catalog_doc,
        manifest_path=str(manifest),
        catalog_dir=str(catalog_dir),
        threshold=threshold,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report
