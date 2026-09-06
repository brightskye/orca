"""Create a fresh, portable Orca vault from a verified release bundle."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import sys
from zipfile import BadZipFile, ZipFile


_TEMPLATE_PREFIX = "orca_memory/vault_template/"
_REQUIRED_RESOURCES = frozenset({
    "AGENTS.md",
    "index.md",
    "System/index.md",
    "System/configuration.md",
    "System/rules.md",
    "System/workflows.md",
})
_CANONICAL_DIRECTORIES = (
    Path("Knowledge"),
    Path("Projects"),
    Path("People"),
    Path("Daily"),
    Path("System/Context"),
)
_INTAKE_DIRECTORIES = (Path("Inbox/Raw"), Path("Inbox/Notes"))
_SYSTEM_DIRECTORIES = (Path("System/Orca Memory"), Path("Archive"))


def _bundle_verifier(bundle: Path):
    """Load the release verifier without importing or caching a module."""
    candidates = (
        bundle / "install.py",
        Path(__file__).resolve().with_name("install_release.py"),
    )
    for candidate in candidates:
        if not candidate.is_file() or candidate.is_symlink():
            continue
        namespace = {"__file__": str(candidate), "__name__": "orca_release_install"}
        try:
            source = candidate.read_bytes()
            exec(compile(source, str(candidate), "exec"), namespace)
        except (OSError, SyntaxError) as exc:
            raise ValueError("Release installer verifier could not be loaded") from exc
        verifier = namespace.get("verify_bundle")
        if callable(verifier):
            return verifier
    raise ValueError("Release does not include a bundle verifier")


def _verify_bundle(bundle: Path) -> tuple[dict, Path, bytes]:
    """Use the sibling installer to verify release membership and hashes."""
    bundle = bundle.expanduser().absolute()
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("Release bundle must be a real directory")
    release_path = bundle / "release.json"
    if release_path.is_symlink() or not release_path.is_file():
        raise ValueError("Release bundle is missing release.json")
    try:
        manifest = _bundle_verifier(bundle)(bundle)
    except (BadZipFile, KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Release verification failed: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise ValueError("Release manifest has no file hashes")
    wheel_name = manifest.get("wheel")
    if (
        not isinstance(wheel_name, str)
        or wheel_name not in manifest["files"]
        or PurePosixPath(wheel_name).name != wheel_name
        or "\\" in wheel_name
        or not wheel_name.endswith(".whl")
    ):
        raise ValueError("Release wheel is missing")
    policy_path = bundle / "orca-memory.example.yaml"
    if "orca-memory.example.yaml" not in manifest["files"] or not policy_path.is_file():
        raise ValueError("Release policy is missing")
    return manifest, bundle / wheel_name, policy_path.read_bytes()


def _read_template_resources(wheel: Path) -> dict[str, bytes]:
    """Read safe regular files under the wheel's vault-template prefix."""
    resources: dict[str, bytes] = {}
    try:
        with ZipFile(wheel) as archive:
            for entry in archive.infolist():
                if not entry.filename.startswith(_TEMPLATE_PREFIX):
                    continue
                relative = entry.filename.removeprefix(_TEMPLATE_PREFIX)
                mode = (entry.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise ValueError("Release contains a symlink vault-template resource")
                if entry.is_dir():
                    relative = relative.removesuffix("/")
                    if not relative:
                        continue
                path = PurePosixPath(relative)
                if (
                    not relative
                    or path.is_absolute()
                    or ":" in relative
                    or "\\" in relative
                    or path.as_posix() != relative
                    or any(part in {"", ".", ".."} for part in path.parts)
                ):
                    raise ValueError("Release contains an invalid vault-template path")
                if entry.is_dir():
                    continue
                if relative in resources:
                    raise ValueError("Release contains a duplicate vault-template resource")
                content = archive.read(entry)
                resources[relative] = content
    except BadZipFile as exc:
        raise ValueError("Release wheel is not a valid zip archive") from exc
    missing = _REQUIRED_RESOURCES - resources.keys()
    if missing:
        raise ValueError(
            "Release wheel is missing vault-template resources: "
            + ", ".join(sorted(missing))
        )
    if "System/Orca Memory/orca-memory.yaml" in resources:
        raise ValueError("Vault template must not provide the generated policy")
    return resources


def _ancestors(path: Path):
    current = path
    while True:
        yield current
        if current.parent == current:
            return
        current = current.parent


def _has_git_marker(path: Path) -> bool:
    for ancestor in _ancestors(path):
        marker = ancestor / ".git"
        if marker.is_symlink() or marker.is_file():
            return True
        # An empty .git directory can be an ordinary placeholder. A checkout
        # has at least a HEAD or config marker (including a linked worktree's
        # gitdir file, handled above).
        if marker.is_dir() and (
            (marker / "HEAD").is_file() or (marker / "config").is_file()
        ):
            return True
    return False


def _validate_destination(destination: Path, bundle: Path) -> Path:
    destination = destination.expanduser()
    if not destination.is_absolute():
        raise ValueError("Vault path must be absolute")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Vault path must be a new directory")
    for parent in _ancestors(destination.parent):
        if parent.is_symlink():
            raise ValueError("Vault path cannot use a symlink parent")
        if parent.exists() and not parent.is_dir():
            raise ValueError("Vault path parent must be a directory")
    try:
        resolved = destination.resolve(strict=False)
        bundle_root = bundle.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Vault path cannot be resolved") from exc
    if _has_git_marker(resolved):
        raise ValueError("Vault path must be outside a Git checkout")
    protected = {
        bundle_root,
        Path(__file__).resolve().parent,
        Path(sys.prefix).resolve(),
        Path(sys.exec_prefix).resolve(),
        Path(getattr(sys, "base_prefix", sys.prefix)).resolve(),
    }
    if bundle_root.name == "package":
        program_root = bundle_root.parent
        if any(
            (program_root / marker).exists()
            for marker in ("env", "hooks.json", "runtime", "bin")
        ):
            protected.add(program_root)
    for root in protected:
        if root == Path(root.anchor):
            continue
        if resolved == root or resolved.is_relative_to(root):
            raise ValueError("Vault path must be outside the release program/runtime")
    return destination


def _output_directories(resources: dict[str, bytes]) -> list[Path]:
    directories: set[Path] = set()
    for relative in _CANONICAL_DIRECTORIES + _INTAKE_DIRECTORIES + _SYSTEM_DIRECTORIES:
        parent = relative
        while parent != Path("."):
            directories.add(parent)
            parent = parent.parent
    for relative in resources:
        parent = Path(*PurePosixPath(relative).parts).parent
        while parent != Path("."):
            directories.add(parent)
            parent = parent.parent
    return sorted(directories, key=lambda path: (len(path.parts), path.as_posix()))


def _write_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
    path.chmod(0o600)


def scaffold(bundle: Path, destination: Path) -> Path:
    """Create and return a new vault populated from a verified release bundle."""
    bundle_path = Path(bundle).expanduser().absolute()
    _manifest, wheel, policy = _verify_bundle(bundle_path)
    resources = _read_template_resources(wheel)
    destination = _validate_destination(Path(destination), bundle_path)

    # Every validation above runs before the first mkdir or file open.
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    for relative in _output_directories(resources):
        (destination / relative).mkdir(mode=0o700, exist_ok=False)
    for relative in sorted(resources):
        target = destination / Path(*PurePosixPath(relative).parts)
        _write_exclusive(target, resources[relative])
    _write_exclusive(destination / "System/Orca Memory/orca-memory.yaml", policy)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault-path", type=Path, required=True,
        help="absolute path for a new Orca vault",
    )
    args = parser.parse_args()
    try:
        created = scaffold(Path(__file__).resolve().parent, args.vault_path)
    except (BadZipFile, OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Scaffold stopped: {exc}\n")
    print(f"Created Orca vault scaffold: {created}")


if __name__ == "__main__":
    main()
