"""Build the portable G0-A ACTIVE-only full-hash source registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from build_corpus_closure import build_closure
from g0a_common import G0AError, resolve_repo_relative, write_json
from source_scope_v2 import active_documents, load_scope


_OLE_CFB_SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")


def probe_media(path: Path, media_type: str) -> dict[str, object]:
    """Report container readability without attempting semantic parsing."""
    if media_type == "application/vnd.ms-excel":
        with path.open("rb") as source:
            signature = source.read(8)
        container_status = "READABLE" if signature == _OLE_CFB_SIGNATURE else "UNREADABLE"
        return {
            "container_status": container_status,
            "semantic_parse_status": "NOT_ATTEMPTED",
            "semantic_parser": None,
        }
    return {
        "container_status": "READABLE",
        "semantic_parse_status": "NOT_APPLICABLE",
        "semantic_parser": None,
    }


def build_registry(repo_root: Path, scope_path: Path) -> dict:
    """Project v2 ACTIVE declarations into the unchanged registry v1 contract."""
    root = repo_root.resolve(strict=True)
    scope = load_scope(scope_path)
    closure = build_closure(root, scope_path)
    closure_by_path = {item["path"]: item for item in closure["documents"]}
    documents: list[dict[str, object]] = []
    for declaration in active_documents(scope):
        raw_path = declaration["path"]
        closure_item = closure_by_path[raw_path]
        source_path = resolve_repo_relative(root, raw_path)
        documents.append(
            {
                "document_id": declaration["document_id"],
                "carrier": declaration["carrier"],
                "role": declaration["role"],
                "media_type": declaration["media"],
                "path": raw_path,
                "size_bytes": closure_item["size_bytes"],
                "sha256": closure_item["sha256"],
                "intake": probe_media(source_path, declaration["media"]),
            }
        )
    return {
        "schema_version": 1,
        "documents": sorted(documents, key=lambda item: str(item["document_id"])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        registry = build_registry(arguments.repo_root, arguments.scope)
        write_json(arguments.out, registry)
    except G0AError as error:
        print(error, file=sys.stderr)
        return 2
    except Exception as error:
        print(G0AError("CHECK_FAILED", type(error).__name__), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
