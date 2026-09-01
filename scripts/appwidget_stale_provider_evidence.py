"""Deterministic evidence storage and immutable input verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterator, Mapping

from appwidget_stale_provider_models import Event


_RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_MANIFEST_NAME = "evidence_sha256.txt"
_PENDING_NAME = ".evidence_pending.json"
_LOCK_NAME = ".run.lock"


class EvidenceInputError(ValueError):
    """Raised when an evidence path or immutable identity is unsafe or wrong."""


class RunLockError(EvidenceInputError):
    """Raised when another process already owns the run evidence ledger."""


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        raise EvidenceInputError("run_id must match YYYYMMDDTHHMMSSZ exactly")
    try:
        datetime.strptime(run_id, "%Y%m%dT%H%M%SZ")
    except ValueError as exc:
        raise EvidenceInputError("run_id contains an invalid UTC date/time") from exc
    return run_id


def make_run_id(now: datetime | None = None) -> str:
    instant = now if now is not None else datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise EvidenceInputError("run_id time must be timezone-aware")
    return instant.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _sync_directory(directory: Path) -> None:
    """Persist rename metadata where the host exposes directory fsync."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        # Windows does not expose portable directory fsync through os.fsync.
        pass
    finally:
        os.close(descriptor)


def _durable_unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
    _sync_directory(path.parent)


@contextmanager
def exclusive_run_lock(bundle_directory: Path | str) -> Iterator[None]:
    """Hold one OS-released writer lock for a complete run operation."""
    directory = Path(bundle_directory).resolve(strict=True)
    lock_path = directory / _LOCK_NAME
    stream = lock_path.open("a+b")
    acquired = False
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ImportError) as exc:
            raise RunLockError(
                "another process already owns the run evidence lock"
            ) from exc
        acquired = True
        yield
    finally:
        if acquired:
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            finally:
                stream.close()
        else:
            stream.close()


def _safe_leaf_name(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\r" in value
        or "\n" in value
        or PureWindowsPath(value).drive
    ):
        raise EvidenceInputError(f"{field} must be a plain file name")
    return value


def _safe_repo_relative(value: str, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvidenceInputError(f"{field} must be a POSIX repo-relative path")
    if "\r" in value or "\n" in value or PureWindowsPath(value).drive:
        raise EvidenceInputError(f"{field} contains an unsafe path form")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise EvidenceInputError(f"{field} must remain beneath the repository root")
    return relative


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise EvidenceInputError(f"{field} must be an exact SHA-256 digest")
    return value.upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _resolve_contained(root: Path, relative: PurePosixPath, field: str) -> Path:
    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise EvidenceInputError(f"{field} is missing or escapes the repository") from exc
    return resolved


@dataclass(frozen=True)
class EvidenceBundle:
    directory: Path

    @classmethod
    def create(cls, root: Path | str, run_id: str) -> "EvidenceBundle":
        checked_run_id = validate_run_id(run_id)
        directory = Path(root) / checked_run_id
        try:
            directory.mkdir(parents=True, exist_ok=False)
            (directory / "snapshots").mkdir()
            (directory / "screenshots").mkdir()
        except FileExistsError as exc:
            raise EvidenceInputError(f"evidence run already exists: {checked_run_id}") from exc
        bundle = cls(directory=directory)
        write_evidence_manifest(directory)
        return bundle

    def write_json(self, relative_name: str, value: object) -> Path:
        name = _safe_leaf_name(relative_name, "evidence JSON name")
        path = self.directory / name
        _transactional_write(self.directory, PurePosixPath(name), _json_bytes(value))
        return path

    def append_event(self, event: Event) -> Path:
        if not isinstance(event, Event):
            raise EvidenceInputError("event must be an Event value object")
        path = self.directory / "events.jsonl"
        try:
            previous = path.read_bytes()
        except FileNotFoundError:
            previous = b""
        except OSError as exc:
            raise EvidenceInputError("events.jsonl cannot be read") from exc
        _validate_json_lines(previous)
        _transactional_write(
            self.directory,
            PurePosixPath("events.jsonl"),
            previous + _json_bytes(asdict(event)),
        )
        return path


def write_evidence_artifact(
    bundle_directory: Path | str,
    relative_path: PurePosixPath | str,
    data: bytes,
) -> Path:
    """Crash-consistently write one bundle artifact and its manifest."""
    directory = Path(bundle_directory).resolve(strict=True)
    relative = _safe_artifact_relative(relative_path)
    path = directory.joinpath(*relative.parts)
    _transactional_write(directory, relative, data)
    return path


def _safe_artifact_relative(relative_path: PurePosixPath | str) -> PurePosixPath:
    raw = str(relative_path)
    relative = PurePosixPath(raw)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or "\\" in raw
        or "\r" in raw
        or "\n" in raw
        or PureWindowsPath(raw).drive
        or relative.as_posix() in {_MANIFEST_NAME, _PENDING_NAME, _LOCK_NAME}
        or relative.name.endswith(".tmp")
    ):
        raise EvidenceInputError("artifact path must remain beneath the bundle")
    return relative


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _artifact_sha256(path: Path) -> str | None:
    try:
        return _sha256_file(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise EvidenceInputError(f"evidence artifact cannot be read: {path.name}") from exc


def _evidence_manifest_bytes(
    directory: Path,
    replacements: Mapping[str, bytes] | None = None,
) -> bytes:
    manifest = directory / _MANIFEST_NAME
    replacement_map = dict(replacements or {})
    entries: dict[str, str] = {}
    for path in directory.rglob("*"):
        if not path.is_file() or path == manifest or path.name.endswith(".tmp"):
            continue
        relative = path.relative_to(directory).as_posix()
        if relative in {_PENDING_NAME, _LOCK_NAME}:
            continue
        entries[relative] = _sha256_file(path).lower()
    for relative, data in replacement_map.items():
        entries[relative] = _sha256_bytes(data).lower()
    data = "".join(
        f"{digest}  {relative}\n" for relative, digest in sorted(entries.items())
    )
    return data.encode("utf-8")


def _validate_json_lines(data: bytes) -> None:
    if not data:
        return
    if not data.endswith(b"\n"):
        raise EvidenceInputError("events.jsonl must contain complete JSON lines")
    try:
        values = [json.loads(line) for line in data.splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceInputError("events.jsonl must contain complete JSON lines") from exc
    if not all(isinstance(value, dict) for value in values):
        raise EvidenceInputError("events.jsonl must contain JSON objects")


def _read_pending_transaction(directory: Path) -> dict[str, Any] | None:
    pending = directory / _PENDING_NAME
    try:
        value = json.loads(pending.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceInputError("pending evidence transaction is invalid") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise EvidenceInputError("pending evidence transaction is invalid")
    required = {
        "schema_version",
        "relative_path",
        "old_artifact_sha256",
        "new_artifact_sha256",
        "old_manifest_sha256",
        "new_manifest_sha256",
    }
    if set(value) != required:
        raise EvidenceInputError("pending evidence transaction schema mismatch")
    relative_path = value.get("relative_path")
    if not isinstance(relative_path, str):
        raise EvidenceInputError("pending evidence transaction path is invalid")
    _safe_artifact_relative(relative_path)
    old_artifact = value.get("old_artifact_sha256")
    if old_artifact is not None:
        if _require_sha256(old_artifact, "pending old artifact SHA-256") != old_artifact:
            raise EvidenceInputError("pending old artifact SHA-256 is not canonical")
    for field in (
        "new_artifact_sha256",
        "old_manifest_sha256",
        "new_manifest_sha256",
    ):
        digest = value.get(field)
        if _require_sha256(digest, f"pending {field}") != digest:
            raise EvidenceInputError(f"pending {field} is not canonical")
    return value


def _recover_pending_transaction(directory: Path) -> None:
    transaction = _read_pending_transaction(directory)
    if transaction is None:
        return
    relative = _safe_artifact_relative(transaction["relative_path"])
    target = directory.joinpath(*relative.parts)
    actual_artifact = _artifact_sha256(target)
    old_artifact = transaction["old_artifact_sha256"]
    new_artifact = transaction["new_artifact_sha256"]
    if actual_artifact not in {old_artifact, new_artifact}:
        raise EvidenceInputError("pending evidence artifact differs from both checkpoints")

    manifest = directory / _MANIFEST_NAME
    try:
        recorded_manifest = manifest.read_bytes()
    except OSError as exc:
        raise EvidenceInputError("pending evidence manifest is missing") from exc
    recorded_digest = _sha256_bytes(recorded_manifest)
    allowed_manifests = {
        transaction["old_manifest_sha256"],
        transaction["new_manifest_sha256"],
    }
    if recorded_digest not in allowed_manifests:
        raise EvidenceInputError("pending evidence manifest differs from both checkpoints")

    canonical_manifest = _evidence_manifest_bytes(directory)
    canonical_digest = _sha256_bytes(canonical_manifest)
    expected_canonical = (
        transaction["new_manifest_sha256"]
        if actual_artifact == new_artifact
        else transaction["old_manifest_sha256"]
    )
    if canonical_digest != expected_canonical:
        raise EvidenceInputError("pending evidence recovery found unrelated file changes")
    if recorded_manifest != canonical_manifest:
        _atomic_write(manifest, canonical_manifest)
    _durable_unlink(directory / _PENDING_NAME)


def _transactional_write(directory: Path, relative: PurePosixPath, data: bytes) -> None:
    if not isinstance(data, bytes):
        raise EvidenceInputError("evidence artifact data must be bytes")
    _recover_pending_transaction(directory)
    manifest = directory / _MANIFEST_NAME
    try:
        recorded_manifest = manifest.read_bytes()
    except OSError as exc:
        raise EvidenceInputError("evidence integrity manifest is missing") from exc
    current_manifest = _evidence_manifest_bytes(directory)
    if recorded_manifest != current_manifest:
        raise EvidenceInputError("evidence integrity manifest mismatch")

    target = directory.joinpath(*relative.parts)
    old_artifact = _artifact_sha256(target)
    new_manifest = _evidence_manifest_bytes(
        directory, {relative.as_posix(): data}
    )
    transaction = {
        "schema_version": 1,
        "relative_path": relative.as_posix(),
        "old_artifact_sha256": old_artifact,
        "new_artifact_sha256": _sha256_bytes(data),
        "old_manifest_sha256": _sha256_bytes(recorded_manifest),
        "new_manifest_sha256": _sha256_bytes(new_manifest),
    }
    _atomic_write(directory / _PENDING_NAME, _json_bytes(transaction))
    _atomic_write(target, data)
    _atomic_write(manifest, new_manifest)
    _durable_unlink(directory / _PENDING_NAME)


def write_evidence_manifest(bundle_directory: Path | str) -> Path:
    directory = Path(bundle_directory).resolve(strict=True)
    _recover_pending_transaction(directory)
    manifest = directory / _MANIFEST_NAME
    _atomic_write(manifest, _evidence_manifest_bytes(directory))
    return manifest


def verify_evidence_manifest(bundle_directory: Path | str) -> None:
    directory = Path(bundle_directory).resolve(strict=True)
    _recover_pending_transaction(directory)
    manifest = directory / _MANIFEST_NAME
    try:
        recorded = manifest.read_bytes()
    except OSError as exc:
        raise EvidenceInputError("evidence integrity manifest is missing") from exc
    if recorded != _evidence_manifest_bytes(directory):
        raise EvidenceInputError("evidence integrity manifest mismatch")


def verify_inputs(repo_root: Path | str, profile: Mapping[str, Any]) -> dict[str, Any]:
    try:
        root = Path(repo_root).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise EvidenceInputError("repository root does not exist") from exc
    if not root.is_dir():
        raise EvidenceInputError("repository root must be a directory")

    try:
        app = profile["app"]
        source_bundle = app["source_bundle"]
    except (KeyError, TypeError) as exc:
        raise EvidenceInputError("profile app source_bundle is required") from exc

    source_relative = _safe_repo_relative(source_bundle, "source_bundle")
    source = _resolve_contained(root, source_relative, "source_bundle")
    if not source.is_dir():
        raise EvidenceInputError("source_bundle must identify a directory")

    try:
        expected_manifest = _require_sha256(
            app["source_manifest_sha256"], "source_manifest_sha256"
        )
        manifest_path = source / "evidence_sha256.txt"
        actual_manifest = _sha256_file(manifest_path)
    except (KeyError, OSError) as exc:
        raise EvidenceInputError("source evidence manifest is missing") from exc
    if actual_manifest != expected_manifest:
        raise EvidenceInputError("source evidence manifest SHA-256 mismatch")

    verified_splits: list[dict[str, Any]] = []
    apk_dir_relative = _safe_repo_relative(
        app.get("apk_dir", "simpleclock_apk"),
        "apk_dir",
    )
    try:
        declared_splits = app["splits"]
    except KeyError as exc:
        raise EvidenceInputError("profile split identities are required") from exc
    for index, declared in enumerate(declared_splits):
        try:
            name, expected_size, expected_digest_raw = declared
        except (TypeError, ValueError) as exc:
            raise EvidenceInputError(f"split[{index}] identity must have three fields") from exc
        checked_name = _safe_leaf_name(name, f"split[{index}] name")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
            raise EvidenceInputError(f"split[{index}] size must be a non-negative integer")
        expected_digest = _require_sha256(expected_digest_raw, f"split[{index}] sha256")
        relative = apk_dir_relative / checked_name
        split_path = _resolve_contained(source, relative, f"split[{index}]")
        if not split_path.is_file():
            raise EvidenceInputError(f"split[{index}] must identify a regular file")
        actual_size = split_path.stat().st_size
        if actual_size != expected_size:
            raise EvidenceInputError(f"split[{index}] size mismatch")
        if _sha256_file(split_path) != expected_digest:
            raise EvidenceInputError(f"split[{index}] SHA-256 mismatch")
        verified_splits.append(
            {
                "logical_id": relative.as_posix(),
                "name": checked_name,
                "size": expected_size,
                "sha256": expected_digest,
            }
        )

    return {
        "package": app.get("package"),
        "signature_token": app.get("signature_token"),
        "source_bundle": source_relative.as_posix(),
        "source_manifest_sha256": expected_manifest,
        "splits": verified_splits,
        "version_code": app.get("version_code"),
        "version_name": app.get("version_name"),
    }
