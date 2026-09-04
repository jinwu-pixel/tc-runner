"""Deterministic primitives for the G0-A source ledger."""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath


class G0AError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_relative(repo_root: Path, raw_path: str) -> Path:
    if "\\" in raw_path:
        raise G0AError("PATH_NOT_POSIX", raw_path)

    pure_path = PurePosixPath(raw_path)
    if (
        pure_path.is_absolute()
        or raw_path.startswith("//")
        or re.match(r"^[A-Za-z]:", raw_path)
        or ".." in pure_path.parts
    ):
        raise G0AError("PATH_OUTSIDE_REPO", raw_path)

    root = repo_root.resolve()
    resolved = (root / Path(*pure_path.parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise G0AError("PATH_OUTSIDE_REPO", raw_path) from error
    return resolved


def write_json(path: Path, value: object) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_bytes(serialized.encode("utf-8"))
