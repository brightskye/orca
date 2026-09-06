"""Encrypted, boundary-checked backups for the private Orca vault.

The backup format deliberately contains no host configuration, raw agent
history, or disposable runtime state.  The only runtime material copied is the
content-minimized operational state needed to continue source cursors and
explicit scope choices.  Encryption is delegated to the locally installed ``gpg`` command;
callers must provide both a recipient and an output path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from collections.abc import Iterable
from typing import Callable

from orca_memory.runtime import SCOPE_CHOICE_SCHEMA, SOURCE_CURSOR_SCHEMA


BACKUP_SCHEMA = "orca-backup/0.1"
MANIFEST_NAME = "manifest.json"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_RUNTIME_STATE_ROOTS = ("source-cursors", "scope-choices")
_PENDING_ROOTS = (
    "queue",
    "retry-spool",
    "publications",
    "project-mappings",
    "owner-review",
    "owner-reviews",
)


class BackupError(ValueError):
    """A backup request or backup payload failed closed."""


class BackupBlockedError(BackupError):
    """The runtime contains work that must be settled before a backup."""


class BackupIntegrityError(BackupError):
    """An encrypted backup failed structural or hash verification."""


CommandRunner = Callable[[list[str]], object]


@dataclass(frozen=True)
class BackupSummary:
    """Summary returned after creating an encrypted backup."""

    output_path: Path
    member_count: int
    total_bytes: int
    manifest_sha256: str


@dataclass(frozen=True)
class BackupVerification:
    """Summary returned after verifying an encrypted backup."""

    backup_path: Path
    member_count: int
    total_bytes: int
    manifest_sha256: str


def create_backup(
    vault_root: Path,
    runtime_root: Path,
    *,
    recipient: str,
    output_path: Path,
    gpg_executable: str = "gpg",
    command_runner: CommandRunner | None = None,
) -> BackupSummary:
    """Create one encrypted backup without copying raw conversations.

    ``recipient`` and ``output_path`` are intentionally required keyword
    arguments.  Existing output is never overwritten.  The source roots are
    checked before any archive work, and pending queue/recovery state blocks
    the operation rather than being silently copied.
    """

    vault, runtime, output = _validate_roots(vault_root, runtime_root, output_path)
    _validate_recipient(recipient)
    _validate_gpg_executable(gpg_executable)
    _reject_pending_runtime(runtime)

    workspace = _temporary_workspace(vault, runtime)
    try:
        tar_path = Path(workspace.name) / "payload.tar"
        manifest, manifest_payload = _build_tar(vault, runtime, tar_path)
        manifest_hash = hashlib.sha256(manifest_payload).hexdigest()
        _encrypt(
            tar_path,
            output,
            recipient=recipient,
            gpg_executable=gpg_executable,
            command_runner=command_runner,
        )
        return BackupSummary(output, len(manifest), sum(item["size"] for item in manifest), manifest_hash)
    except BackupError:
        _remove_new_output(output)
        raise
    except (OSError, tarfile.TarError, ValueError, TypeError, json.JSONDecodeError) as exc:
        _remove_new_output(output)
        raise BackupError(f"backup creation failed: {exc}") from exc
    finally:
        workspace.cleanup()


def verify_backup(
    backup_path: Path,
    *,
    gpg_executable: str = "gpg",
    command_runner: CommandRunner | None = None,
) -> BackupVerification:
    """Decrypt to a private temporary file and verify every archived hash."""

    backup = _validate_backup_path(backup_path)
    _validate_gpg_executable(gpg_executable)
    workspace = _temporary_verification_workspace()
    try:
        tar_path = Path(workspace.name) / "payload.tar"
        _decrypt(
            backup,
            tar_path,
            gpg_executable=gpg_executable,
            command_runner=command_runner,
        )
        manifest, manifest_payload = _verify_tar(tar_path)
        return BackupVerification(
            backup,
            len(manifest),
            sum(item["size"] for item in manifest),
            hashlib.sha256(manifest_payload).hexdigest(),
        )
    except BackupIntegrityError:
        raise
    except (OSError, tarfile.TarError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise BackupIntegrityError(f"backup verification failed: {exc}") from exc
    finally:
        workspace.cleanup()


def decrypt_backup_to_staging(
    backup_path: Path,
    *,
    staging_path: Path | None = None,
    vault_root: Path | None = None,
    runtime_root: Path | None = None,
    project_roots: Iterable[Path] = (),
    gpg_executable: str = "gpg",
    command_runner: CommandRunner | None = None,
) -> Path:
    """Validate a backup, then expose its contents in a new private staging dir.

    The destination must not already exist.  When the live ``vault_root`` and
    ``runtime_root`` are supplied, the destination and temporary workspace are
    also checked to be outside both roots.  ``project_roots`` adds configured
    checkout boundaries; detected Git worktree roots are protected as well.
    This makes it impossible for a restore to overwrite a live vault or
    runtime, and keeps all files hidden in a private temporary directory until
    manifest and content hashes pass.
    """

    backup = _validate_backup_path(backup_path)
    _validate_gpg_executable(gpg_executable)
    protected_roots = _protected_roots(vault_root, runtime_root, project_roots)
    destination = _validate_staging_path(staging_path, protected_roots)
    workspace = _temporary_verification_workspace(protected_roots)
    published = False
    try:
        tar_path = Path(workspace.name) / "payload.tar"
        _decrypt(
            backup,
            tar_path,
            gpg_executable=gpg_executable,
            command_runner=command_runner,
        )
        manifest, _ = _verify_tar(tar_path)
        hidden = Path(workspace.name) / "staging"
        hidden.mkdir(mode=0o700)
        _extract_verified_tar(tar_path, hidden, manifest)
        if destination is None:
            destination = Path(tempfile.mkdtemp(prefix="orca-restore-"))
            os.chmod(destination, 0o700)
            if destination.is_symlink():
                raise BackupIntegrityError("restore staging path is a symlink")
            _assert_outside_protected(destination, protected_roots)
        else:
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.rename(hidden, destination)
            published = True
            return destination
        os.rename(hidden, destination)
        published = True
        return destination
    except BackupIntegrityError:
        raise
    except (OSError, tarfile.TarError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise BackupIntegrityError(f"backup restore failed: {exc}") from exc
    finally:
        workspace.cleanup()
        if not published and destination is not None and destination.exists():
            _remove_tree(destination)


def _validate_roots(vault_root: Path, runtime_root: Path, output_path: Path) -> tuple[Path, Path, Path]:
    if not isinstance(vault_root, Path) or not isinstance(runtime_root, Path):
        raise BackupError("vault_root and runtime_root must be Paths")
    if not isinstance(output_path, Path) or not output_path.is_absolute():
        raise BackupError("backup output_path must be an absolute path")
    if vault_root.is_symlink() or runtime_root.is_symlink():
        raise BackupError("vault and runtime roots must not be symlinks")
    vault = vault_root.resolve(strict=True)
    runtime = runtime_root.resolve(strict=True)
    if not vault.is_dir() or not runtime.is_dir():
        raise BackupError("vault and runtime roots must be directories")
    if vault == runtime or vault in runtime.parents or runtime in vault.parents:
        raise BackupError("vault and runtime roots must be separate")
    output = output_path.resolve(strict=False)
    if output_path.is_symlink():
        raise BackupError("backup output must not be a symlink")
    if output == vault or vault in output.parents or output == runtime or runtime in output.parents:
        raise BackupError("backup output must be outside vault and runtime")
    if output.exists():
        raise BackupError("backup output already exists")
    if output.name in {"", ".", ".."}:
        raise BackupError("backup output must be a file path")
    return vault, runtime, output


def _validate_backup_path(backup_path: Path) -> Path:
    if not isinstance(backup_path, Path) or not backup_path.is_absolute():
        raise BackupIntegrityError("backup path must be an absolute path")
    if backup_path.is_symlink() or not backup_path.is_file():
        raise BackupIntegrityError("backup path must be a regular file")
    if backup_path.stat().st_mode & 0o077:
        raise BackupIntegrityError("backup file permissions must be private")
    return backup_path.resolve(strict=True)


def _validate_staging_path(
    staging_path: Path | None,
    protected_roots: tuple[Path, ...] = (),
) -> Path | None:
    if staging_path is None:
        return None
    if not isinstance(staging_path, Path) or not staging_path.is_absolute():
        raise BackupError("staging_path must be an absolute path")
    if staging_path.exists() or staging_path.is_symlink():
        raise BackupError("staging_path must not already exist")
    destination = staging_path.resolve(strict=False)
    _assert_outside_protected(destination, protected_roots)
    return destination


def _assert_outside_protected(
    destination: Path,
    protected_roots: tuple[Path, ...],
) -> None:
    worktree_root = _git_worktree_root(destination)
    boundaries = protected_roots + ((worktree_root,) if worktree_root is not None else ())
    if any(root == destination or root in destination.parents for root in boundaries):
        raise BackupError("staging_path must be outside protected roots")


def _validate_recipient(recipient: str) -> None:
    if not isinstance(recipient, str) or not recipient.strip() or "\x00" in recipient:
        raise BackupError("an explicit GPG recipient is required")


def _validate_gpg_executable(gpg_executable: str) -> None:
    if not isinstance(gpg_executable, str) or not gpg_executable or "\x00" in gpg_executable:
        raise BackupError("invalid GPG executable")


def _temporary_workspace(vault: Path, runtime: Path):
    workspace = tempfile.TemporaryDirectory(prefix="orca-backup-")
    path = Path(workspace.name).resolve()
    if path == vault or vault in path.parents or path == runtime or runtime in path.parents:
        workspace.cleanup()
        raise BackupError("temporary backup workspace overlaps a source root")
    if _git_worktree_root(path) is not None:
        workspace.cleanup()
        raise BackupError("temporary backup workspace overlaps a Git worktree")
    os.chmod(path, 0o700)
    return workspace


def _temporary_verification_workspace(protected_roots: tuple[Path, ...] = ()):
    workspace = tempfile.TemporaryDirectory(prefix="orca-backup-verify-")
    path = Path(workspace.name).resolve()
    if any(root == path or root in path.parents for root in protected_roots):
        workspace.cleanup()
        raise BackupError("temporary verification workspace overlaps a protected root")
    if _git_worktree_root(path) is not None:
        workspace.cleanup()
        raise BackupError("temporary verification workspace overlaps a Git worktree")
    os.chmod(workspace.name, 0o700)
    return workspace


def _protected_roots(
    vault_root: Path | None,
    runtime_root: Path | None,
    project_roots: Iterable[Path] = (),
) -> tuple[Path, ...]:
    roots: list[Path] = []
    for label, root in (("vault_root", vault_root), ("runtime_root", runtime_root)):
        if root is None:
            continue
        if not isinstance(root, Path) or root.is_symlink():
            raise BackupError(f"{label} must be a non-symlink directory")
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise BackupError(f"{label} must be a directory")
        roots.append(resolved)

    live_roots = tuple(roots)
    for index, root in enumerate(project_roots):
        if not isinstance(root, Path) or not root.is_absolute():
            raise BackupError(f"project_roots[{index}] must be an absolute path")
        try:
            roots.append(root.resolve(strict=False))
        except OSError as exc:
            raise BackupError(f"project_roots[{index}] cannot be normalized") from exc

    # A runtime may live in a checkout for compatibility with the existing
    # local layout.  Its Git root is protected as a staging boundary without
    # rejecting the runtime itself.
    for root in tuple(roots):
        worktree_root = _git_worktree_root(root)
        if worktree_root is not None:
            roots.append(worktree_root)

    if len(live_roots) == 2 and (
        live_roots[0] == live_roots[1]
        or live_roots[0] in live_roots[1].parents
        or live_roots[1] in live_roots[0].parents
    ):
        raise BackupError("vault and runtime roots must be separate")
    return tuple(roots)


def _git_worktree_root(path: Path) -> Path | None:
    """Find one valid Git worktree boundary containing ``path``.

    Empty ``.git`` directories are ignored as insufficient evidence.  A
    linked-worktree ``.git`` file and a normal marker with its core entries are
    accepted.  Partial or unreadable markers fail closed.
    """

    probe = path
    while not probe.exists() and not probe.is_symlink() and probe != probe.parent:
        probe = probe.parent
    for candidate in (probe, *probe.parents):
        marker = candidate / ".git"
        try:
            marker_info = marker.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise BackupError("cannot inspect Git worktree boundary") from exc
        if stat.S_ISLNK(marker_info.st_mode):
            try:
                marker = marker.resolve(strict=True)
                marker_info = marker.stat()
            except OSError as exc:
                raise BackupError("Git worktree marker is unreadable") from exc
        if stat.S_ISREG(marker_info.st_mode):
            try:
                lines = marker.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                raise BackupError("Git worktree marker is unreadable") from exc
            if len(lines) != 1 or not lines[0].startswith("gitdir: "):
                raise BackupError("ambiguous Git worktree marker")
            raw_gitdir = lines[0][len("gitdir: ") :].strip()
            if not raw_gitdir or "\x00" in raw_gitdir:
                raise BackupError("ambiguous Git worktree marker")
            gitdir = Path(raw_gitdir)
            if not gitdir.is_absolute():
                gitdir = candidate / gitdir
            try:
                if not gitdir.resolve(strict=True).is_dir():
                    raise BackupError("Git worktree marker is unreadable")
            except OSError as exc:
                raise BackupError("Git worktree marker is unreadable") from exc
            try:
                return Path(os.path.normcase(str(candidate.resolve(strict=True))))
            except OSError as exc:
                raise BackupError("Git worktree root is unreadable") from exc
        if not stat.S_ISDIR(marker_info.st_mode):
            raise BackupError("ambiguous Git worktree marker")

        expected = {"HEAD": stat.S_ISREG, "config": stat.S_ISREG,
                    "objects": stat.S_ISDIR, "refs": stat.S_ISDIR}
        present = False
        valid = True
        found: set[str] = set()
        for name, kind in expected.items():
            entry = marker / name
            try:
                info = entry.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise BackupError("Git worktree marker is unreadable") from exc
            present = True
            found.add(name)
            valid = valid and not stat.S_ISLNK(info.st_mode) and kind(info.st_mode)
        if not present:
            continue
        if not valid or found != set(expected):
            raise BackupError("ambiguous Git worktree marker")
        try:
            return Path(os.path.normcase(str(candidate.resolve(strict=True))))
        except OSError as exc:
            raise BackupError("Git worktree root is unreadable") from exc
    return None
def _reject_pending_runtime(runtime: Path) -> None:
    for root_name in _PENDING_ROOTS:
        root = runtime / root_name
        if not root.exists() and not root.is_symlink():
            continue
        if root.is_symlink():
            raise BackupBlockedError(f"pending runtime state is unsafe: {root_name}")
        if not root.is_dir():
            raise BackupError(f"pending runtime state root is not a directory: {root_name}")
        _reject_special_entries(root)
        if any(root.iterdir()):
            raise BackupBlockedError(f"pending runtime state must be settled: {root_name}")


def _reject_special_entries(root: Path) -> None:
    for path in root.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) and not stat.S_ISREG(info.st_mode):
            raise BackupError(f"special or symlink runtime entry is not allowed: {path}")


def _build_tar(vault: Path, runtime: Path, tar_path: Path) -> tuple[list[dict[str, object]], bytes]:
    entries = _collect_source_entries(vault, "vault")
    for state_root in _RUNTIME_STATE_ROOTS:
        source = runtime / state_root
        if not source.exists():
            continue
        if source.is_symlink() or not source.is_dir():
            raise BackupError(f"runtime state root is not a directory: {state_root}")
        entries.extend(_collect_source_entries(source, f"runtime/{state_root}", validate_state=state_root))
    entries.sort(key=lambda item: item["archive_path"])
    manifest: list[dict[str, object]] = []
    with tarfile.open(tar_path, mode="w", format=tarfile.PAX_FORMAT) as archive:
        _add_directory(archive, "vault")
        for state_root in _RUNTIME_STATE_ROOTS:
            if (runtime / state_root).exists():
                _add_directory(archive, f"runtime/{state_root}")
        for entry in entries:
            source = entry["source"]
            archive_path = entry["archive_path"]
            assert isinstance(source, Path)
            assert isinstance(archive_path, str)
            digest, size = _add_file(archive, source, archive_path)
            manifest.append({"path": archive_path, "size": size, "sha256": digest})
        manifest_payload = _manifest_payload(manifest)
        info = tarfile.TarInfo(MANIFEST_NAME)
        info.size = len(manifest_payload)
        info.mode = 0o600
        info.mtime = 0
        archive.addfile(info, fileobj=_BytesReader(manifest_payload))
    os.chmod(tar_path, 0o600)
    return manifest, manifest_payload


def _collect_source_entries(
    root: Path,
    prefix: str,
    *,
    validate_state: str | None = None,
) -> list[dict[str, object]]:
    if root.is_symlink() or not root.is_dir():
        raise BackupError(f"source root is not a regular directory: {root}")
    result: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise BackupError(f"source symlink is not allowed: {path}")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise BackupError(f"special source file is not allowed: {path}")
        relative = path.relative_to(root).as_posix()
        archive_path = f"{prefix}/{relative}"
        _validate_relative(archive_path)
        if validate_state is not None:
            _validate_runtime_state(path, validate_state)
        result.append({"source": path, "archive_path": archive_path})
    return result


def _validate_runtime_state(path: Path, state_root: str) -> None:
    if path.suffix != ".json":
        raise BackupError(f"unexpected runtime state file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError(f"invalid runtime state file: {path}") from exc
    if not isinstance(value, dict):
        raise BackupError(f"runtime state must be a JSON object: {path}")
    if state_root == "source-cursors":
        expected = {"schema", "connector_id", "conversation_id", "source_path", "processed_through"}
        if (
            set(value) != expected
            or value.get("schema") != SOURCE_CURSOR_SCHEMA
            or not isinstance(value.get("connector_id"), str)
            or not _SAFE_ID.fullmatch(value["connector_id"])
            or not isinstance(value.get("conversation_id"), str)
            or not _SAFE_ID.fullmatch(value["conversation_id"])
            or not isinstance(value.get("source_path"), str)
            or not Path(value["source_path"]).is_absolute()
            or not isinstance(value.get("processed_through"), int)
            or isinstance(value["processed_through"], bool)
            or value["processed_through"] < 0
        ):
            raise BackupError(f"invalid source cursor state: {path}")
    elif state_root == "scope-choices":
        expected = {"schema", "conversation_id", "scope_kind"}
        if (
            set(value) != expected
            or value.get("schema") != SCOPE_CHOICE_SCHEMA
            or not isinstance(value.get("conversation_id"), str)
            or not _SAFE_ID.fullmatch(value["conversation_id"])
            or value.get("scope_kind") not in {"general", "unassigned"}
        ):
            raise BackupError(f"invalid scope choice state: {path}")


def _add_directory(archive: tarfile.TarFile, name: str) -> None:
    info = tarfile.TarInfo(name.rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = 0o700
    info.mtime = 0
    archive.addfile(info)


def _add_file(archive: tarfile.TarFile, source: Path, archive_path: str) -> tuple[str, int]:
    _validate_relative(archive_path)
    info = source.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise BackupError(f"source changed to a non-regular file: {source}")
    resolved = source.resolve(strict=True)
    if resolved != source:
        raise BackupError(f"source path escapes its root: {source}")
    tar_info = tarfile.TarInfo(archive_path)
    tar_info.size = info.st_size
    tar_info.mode = 0o600
    tar_info.mtime = 0
    descriptor_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        descriptor_flags |= os.O_NOFOLLOW
    descriptor = os.open(source, descriptor_flags)
    try:
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode) or current.st_size != info.st_size:
            raise BackupError(f"source changed while archiving: {source}")
        with os.fdopen(descriptor, "rb") as stream:
            reader = _HashingReader(stream)
            archive.addfile(tar_info, fileobj=reader)
            if reader.size != info.st_size:
                raise BackupError(f"source size changed while archiving: {source}")
            return reader.hexdigest, reader.size
    except Exception:
        # fdopen owns the descriptor after success; on an early os.fdopen
        # failure the explicit close keeps the private workspace leak-free.
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _manifest_payload(manifest: list[dict[str, object]]) -> bytes:
    payload = {"schema": BACKUP_SCHEMA, "members": manifest}
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _verify_tar(tar_path: Path) -> tuple[list[dict[str, object]], bytes]:
    seen: set[str] = set()
    manifest_payload: bytes | None = None
    manifest: list[dict[str, object]] | None = None
    with tarfile.open(tar_path, mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            _validate_relative(member.name)
            _validate_archive_member_scope(member.name, is_directory=member.isdir())
            if member.name in seen:
                raise BackupIntegrityError(f"duplicate archive member: {member.name}")
            seen.add(member.name)
            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise BackupIntegrityError(f"unsupported archive member type: {member.name}")
            if member.name == MANIFEST_NAME:
                if not member.isfile() or member.size > 16 * 1024 * 1024:
                    raise BackupIntegrityError("invalid backup manifest member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise BackupIntegrityError("backup manifest cannot be read")
                manifest_payload = stream.read(member.size + 1)
                if len(manifest_payload) != member.size:
                    raise BackupIntegrityError("backup manifest read was truncated")
                manifest = _parse_manifest(manifest_payload)
        if manifest_payload is None or manifest is None:
            raise BackupIntegrityError("backup manifest is missing")
        expected = {entry["path"] for entry in manifest}
        actual = {member.name for member in members if member.isfile() and member.name != MANIFEST_NAME}
        if expected != actual:
            raise BackupIntegrityError("backup manifest does not match archive files")
        by_path = {entry["path"]: entry for entry in manifest}
        for member in members:
            if not member.isfile() or member.name == MANIFEST_NAME:
                continue
            entry = by_path[member.name]
            stream = archive.extractfile(member)
            if stream is None:
                raise BackupIntegrityError(f"archive member cannot be read: {member.name}")
            digest, size = _hash_stream(stream)
            if size != entry["size"] or size != member.size or digest != entry["sha256"]:
                raise BackupIntegrityError(f"archive member hash mismatch: {member.name}")
    return manifest, manifest_payload


def _parse_manifest(payload: bytes) -> list[dict[str, object]]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupIntegrityError("backup manifest is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict) or set(value) != {"schema", "members"}:
        raise BackupIntegrityError("backup manifest has an invalid schema")
    if value.get("schema") != BACKUP_SCHEMA or not isinstance(value.get("members"), list):
        raise BackupIntegrityError("backup manifest has an invalid schema")
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in value["members"]:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise BackupIntegrityError("backup manifest member is invalid")
        path = item.get("path")
        size = item.get("size")
        digest = item.get("sha256")
        if (
            not isinstance(path, str)
            or path == MANIFEST_NAME
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or not isinstance(digest, str)
            or not _HASH.fullmatch(digest)
        ):
            raise BackupIntegrityError("backup manifest member is invalid")
        _validate_relative(path)
        if path in seen:
            raise BackupIntegrityError("backup manifest contains duplicate paths")
        seen.add(path)
        result.append({"path": path, "size": size, "sha256": digest})
    if result != sorted(result, key=lambda item: item["path"]):
        raise BackupIntegrityError("backup manifest members are not sorted")
    return result


def _extract_verified_tar(
    tar_path: Path,
    destination: Path,
    manifest: list[dict[str, object]],
) -> None:
    by_path = {entry["path"]: entry for entry in manifest}
    with tarfile.open(tar_path, mode="r:") as archive:
        for member in archive.getmembers():
            target = _safe_destination(destination, member.name)
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.chmod(target, 0o700)
                continue
            if member.name == MANIFEST_NAME:
                expected = archive.extractfile(member)
                if expected is None:
                    raise BackupIntegrityError("backup manifest cannot be extracted")
                _write_extracted(target, expected, member.size, 0o600)
                continue
            entry = by_path.get(member.name)
            if entry is None:
                raise BackupIntegrityError(f"unlisted archive member: {member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise BackupIntegrityError(f"archive member cannot be extracted: {member.name}")
            _write_extracted(target, stream, member.size, 0o600)


def _write_extracted(path: Path, stream, expected_size: int, mode: int) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as output:
            remaining = expected_size
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise BackupIntegrityError(f"archive member was truncated during extraction: {path}")
                output.write(chunk)
                remaining -= len(chunk)
            if stream.read(1):
                raise BackupIntegrityError(f"archive member exceeded its declared size: {path}")
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _safe_destination(root: Path, relative: str) -> Path:
    _validate_relative(relative)
    target = (root / PurePosixPath(relative)).resolve(strict=False)
    resolved_root = root.resolve(strict=True)
    if target != resolved_root and resolved_root not in target.parents:
        raise BackupIntegrityError(f"archive member escapes staging: {relative}")
    return target


def _validate_relative(value: str) -> None:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise BackupIntegrityError(f"invalid relative archive path: {value!r}")
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise BackupIntegrityError(f"path escapes archive root: {value!r}")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or "." in parsed.parts:
        raise BackupIntegrityError(f"path escapes archive root: {value!r}")


def _validate_archive_member_scope(value: str, *, is_directory: bool) -> None:
    if value == MANIFEST_NAME:
        if is_directory:
            raise BackupIntegrityError("backup manifest must be a regular file")
        return
    allowed_roots = (
        "vault",
        "runtime/source-cursors",
        "runtime/scope-choices",
    )
    if value in allowed_roots:
        if not is_directory:
            raise BackupIntegrityError(f"archive root must be a directory: {value}")
        return
    if not any(value.startswith(root + "/") for root in allowed_roots):
        raise BackupIntegrityError(f"archive member is outside the backup boundary: {value}")


def _hash_stream(stream) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


class _HashingReader:
    def __init__(self, stream) -> None:
        self.stream = stream
        self.digest = hashlib.sha256()
        self.size = 0

    @property
    def hexdigest(self) -> str:
        return self.digest.hexdigest()

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        if data:
            self.digest.update(data)
            self.size += len(data)
        return data


class _BytesReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = len(self.payload) - self.offset
        start = self.offset
        self.offset = min(len(self.payload), start + size)
        return self.payload[start : self.offset]


def _encrypt(
    tar_path: Path,
    output: Path,
    *,
    recipient: str,
    gpg_executable: str,
    command_runner: CommandRunner | None,
) -> None:
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if output.parent.is_symlink() or not output.parent.is_dir():
        raise BackupError("backup output parent must be a regular directory")
    _run_gpg(
        [
            gpg_executable,
            "--batch",
            "--no-tty",
            "--trust-model",
            "always",
            "--recipient",
            recipient,
            "--output",
            str(output),
            "--encrypt",
            str(tar_path),
        ],
        command_runner,
    )
    if not output.is_file() or output.is_symlink():
        raise BackupError("GPG did not create a regular backup file")
    os.chmod(output, 0o600)


def _decrypt(
    backup: Path,
    tar_path: Path,
    *,
    gpg_executable: str,
    command_runner: CommandRunner | None,
) -> None:
    _run_gpg(
        [
            gpg_executable,
            "--batch",
            "--no-tty",
            "--output",
            str(tar_path),
            "--decrypt",
            str(backup),
        ],
        command_runner,
    )
    if not tar_path.is_file() or tar_path.is_symlink():
        raise BackupIntegrityError("GPG did not create a regular decrypted payload")
    os.chmod(tar_path, 0o600)


def _run_gpg(command: list[str], command_runner: CommandRunner | None) -> None:
    try:
        if command_runner is None:
            completed = subprocess.run(
                command,
                check=True,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            completed = command_runner(command)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupError(f"GPG command failed: {exc}") from exc
    if completed is not None and getattr(completed, "returncode", 0) not in (0, None):
        raise BackupError(f"GPG command failed with exit code {completed.returncode}")


def _remove_new_output(path: Path) -> None:
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


__all__ = [
    "BACKUP_SCHEMA",
    "BackupBlockedError",
    "BackupError",
    "BackupIntegrityError",
    "BackupSummary",
    "BackupVerification",
    "MANIFEST_NAME",
    "create_backup",
    "decrypt_backup_to_staging",
    "verify_backup",
]
