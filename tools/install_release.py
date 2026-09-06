"""Install an extracted Orca release without a source checkout (Python 3.11+)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import sys
import types
from zipfile import BadZipFile, ZipFile


SKILL_NAMES = ("orca-conversation", "orca-wiki")


def _absolute(path: Path) -> Path:
    """Expand a user path without following symlinks."""
    return path.expanduser().absolute()


def _resolved(path: Path) -> Path:
    """Return the host-normalized path used for containment checks."""
    return _absolute(path).resolve()


def _overlaps(first: Path, second: Path) -> bool:
    """Return whether two normalized paths contain one another."""
    return (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    )


def _yaml_scalar(value: Path) -> str:
    """Render a path as a safe YAML scalar without requiring PyYAML."""
    return json.dumps(str(value))


def _set_host_field(template: str, field: str, value: Path) -> str:
    """Replace or append one top-level scalar in a safe host template."""
    rendered = _yaml_scalar(value)
    lines = template.splitlines()
    prefix = f"{field}:"
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(prefix) and (
            len(stripped) == len(prefix) or stripped[len(prefix)].isspace()
        ):
            indentation = line[: len(line) - len(stripped)]
            lines[index] = f"{indentation}{field}: {rendered}"
            return "\n".join(lines).rstrip("\n") + "\n"
    lines.append(f"{field}: {rendered}")
    return "\n".join(lines).rstrip("\n") + "\n"


def _host_template(template: str, runtime_path: Path, vault_path: Path | None) -> str:
    """Bind generated host configuration to its private runtime and vault."""
    rendered = _set_host_field(template, "runtime_path", runtime_path)
    if vault_path is not None:
        rendered = _set_host_field(rendered, "vault_path", vault_path)
    return rendered


def bundled_skills(wheel: Path) -> dict[str, bytes]:
    """Read the agent resources from the same verified wheel as the runtime."""
    resources = {}
    prefix = "orca_memory/skills/"
    with ZipFile(wheel) as archive:
        for entry in archive.infolist():
            if not entry.filename.startswith(prefix) or entry.is_dir():
                continue
            relative = entry.filename.removeprefix(prefix)
            path = PurePosixPath(relative)
            if (
                len(path.parts) < 2 or path.parts[0] not in SKILL_NAMES
                or ".." in path.parts or "\\" in relative
                or path.as_posix() != relative or relative in resources
                or (entry.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Release contains an invalid skill resource")
            resources[relative] = archive.read(entry)
    for name in SKILL_NAMES:
        if f"{name}/SKILL.md" not in resources:
            raise ValueError(f"Release wheel is missing skill: {name}")
    return resources


def check_skill_destination(directory: Path) -> None:
    """Preserve existing skills; discovery links require unused names."""
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError("Skills destination must be a real directory")
    for name in SKILL_NAMES:
        target = directory / name
        if target.exists() or target.is_symlink():
            raise ValueError(
                f"Existing skill requires reconciliation before discovery linking: {target}. "
                "Preserve it and move it aside, or select a new --skills-dir."
            )


def _load_vault_scaffolder(bundle: Path, manifest: dict) -> tuple[object, object]:
    """Load the hashed release scaffolder without creating a bytecode cache."""
    if "scaffold_vault.py" not in manifest["files"]:
        raise ValueError("Release does not include vault scaffolding")
    bundled = bundle / "scaffold_vault.py"
    if bundled.is_symlink() or not bundled.is_file():
        raise ValueError("Release vault scaffolder is invalid")
    module = types.ModuleType("orca_release_scaffold_vault")
    module.__file__ = str(bundled)
    try:
        source = bundled.read_bytes()
        exec(compile(source, str(bundled), "exec"), module.__dict__)
    except (OSError, SyntaxError, ImportError) as exc:
        raise ValueError("Release vault scaffolder could not be loaded") from exc
    scaffold = getattr(module, "scaffold", None)
    validate = getattr(module, "_validate_destination", None)
    if not callable(scaffold) or not callable(validate):
        raise ValueError("Release vault scaffolder lacks destination preflight")
    return scaffold, validate


def verify_bundle(bundle: Path) -> dict:
    """Check release membership and bytes before creating an installation."""
    manifest = json.loads((bundle / "release.json").read_text())
    expected = manifest["files"]
    actual = {p.name for p in bundle.iterdir()}
    if actual != set(expected) | {"release.json"}:
        raise ValueError("Release files do not match release.json")
    for name, digest in expected.items():
        path = bundle / name
        if Path(name).name != name or path.is_symlink() or not path.is_file():
            raise ValueError("Release contains an invalid file")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Release checksum mismatch: {name}")
    if manifest["wheel"] not in expected or not manifest["wheel"].endswith(".whl"):
        raise ValueError("Release wheel is missing")
    return manifest


def install(
    bundle: Path,
    prefix: Path,
    host_config: Path,
    skills_dir: Path,
    *,
    vault_path: Path | None = None,
    create_vault: bool = False,
) -> None:
    """Create a fresh self-contained installation from an extracted release.

    The prefix cannot exist. A failed install is left for inspection, never
    removed or silently reused. The application, environment, package copy,
    private runtime, and physical skills all live below the prefix. The
    selected host skills directory receives only discovery symlinks. Existing
    host configuration is preserved. Vault scaffolding is opt-in and requires
    both ``--create-vault`` and an explicit vault path.
    """
    bundle = _resolved(bundle)
    manifest = verify_bundle(bundle)
    prefix_arg = _absolute(prefix)
    host_arg = _absolute(host_config)
    skills_arg = _absolute(skills_dir)
    if prefix_arg.exists() or prefix_arg.is_symlink():
        raise ValueError("Install directory already exists; select a new --prefix")
    if host_arg.is_symlink():
        raise ValueError("Select the real host config path instead of a symlink")
    if host_arg.exists() and not host_arg.is_file():
        raise ValueError("Host config exists but is not a file")
    if skills_arg.is_symlink() or (skills_arg.exists() and not skills_arg.is_dir()):
        raise ValueError("Skills destination must be a real directory")

    prefix = prefix_arg.resolve()
    host_config = host_arg.resolve()
    skills_dir = skills_arg.resolve()
    default_host_config = (prefix / "config/host.yaml").resolve()
    if host_config != default_host_config and host_config.is_relative_to(prefix):
        raise ValueError("Host configuration inside the installation must use config/host.yaml")
    if _overlaps(prefix, bundle):
        raise ValueError("Install destination must be separate from the release bundle")
    if _overlaps(host_config, bundle) or _overlaps(skills_dir, bundle):
        raise ValueError("Install destinations must be separate from the release bundle")
    if _overlaps(skills_dir, prefix):
        raise ValueError("Skills destination must be separate from the installation")
    if _overlaps(host_config, skills_dir):
        raise ValueError("Skills destination must be separate from the host config")

    runtime = prefix / "runtime"
    if vault_path is not None:
        vault_input = vault_path.expanduser()
        if not vault_input.is_absolute():
            raise ValueError("Vault path must be absolute")
        vault_arg = vault_input.absolute()
        if vault_arg.is_symlink():
            raise ValueError("Vault path must be a real destination path")
        vault = vault_arg.resolve()
        if _overlaps(vault, prefix) or _overlaps(vault, runtime):
            raise ValueError("Vault must be separate from the installation runtime")
        if _overlaps(vault, skills_dir) or _overlaps(vault, host_config):
            raise ValueError("Vault must be separate from skills and host configuration")
        if _overlaps(vault, bundle):
            raise ValueError("Vault must be separate from the release bundle")
        if create_vault and vault.exists():
            raise ValueError("Vault destination already exists; choose a new path")
    elif create_vault:
        raise ValueError("--create-vault requires --vault-path")
    else:
        vault = None

    if vault_path is not None and host_config.exists():
        raise ValueError(
            "Cannot bind --vault-path while preserving an existing host config; "
            "omit --vault-path or select a new host config"
        )

    scaffold = validate_vault = None
    if create_vault:
        scaffold, validate_vault = _load_vault_scaffolder(bundle, manifest)
        validate_vault(vault, bundle)

    resources = bundled_skills(bundle / manifest["wheel"])
    check_skill_destination(skills_dir)
    uv = shutil.which("uv")
    if uv is None:
        raise ValueError("Install uv before running this installer")

    prefix.mkdir(parents=True, mode=0o700)
    runtime.mkdir(mode=0o700)
    cache = prefix / "cache" / "uv"
    cache.mkdir(parents=True, mode=0o700)
    uv_environment = os.environ.copy()
    uv_environment["UV_CACHE_DIR"] = str(cache)
    uv_environment["UV_NO_MANAGED_PYTHON"] = "1"

    python = prefix / "env/bin/python"
    subprocess.run([
        uv, "venv", "--no-managed-python", "--python", sys.executable,
        str(prefix / "env"),
    ], check=True, env=uv_environment)
    subprocess.run([
        uv, "pip", "install", "--no-managed-python", "--python", str(python),
        "--require-hashes", "-r", str(bundle / "requirements.txt"),
    ], check=True, env=uv_environment)
    subprocess.run([
        uv, "pip", "install", "--no-managed-python", "--python", str(python),
        "--no-deps", str(bundle / manifest["wheel"]),
    ], check=True, env=uv_environment)
    subprocess.run([
        uv, "pip", "check", "--no-managed-python", "--python", str(python),
    ], check=True, env=uv_environment)

    package = prefix / "package"
    package.mkdir(mode=0o700)
    for name in sorted(manifest["files"]):
        shutil.copyfile(bundle / name, package / name)
    shutil.copyfile(bundle / "release.json", package / "release.json")

    host_config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not host_config.exists():
        host_config.write_text(
            _host_template(
                (bundle / "host.example.yaml").read_text(encoding="utf-8"),
                runtime,
                vault,
            ),
            encoding="utf-8",
        )
        host_config.chmod(0o600)

    commands = prefix / "bin"
    commands.mkdir()
    launchers = {
        "orca": "exec " + shlex.join([
            str(python), "-I", "-m", "orca_memory.cli",
            "--host-config", str(host_config),
        ]) + ' "$@"\n',
        "orca-codex-hook": "export ORCA_HOST_CONFIG=" + shlex.quote(str(host_config))
        + "\nexec " + shlex.join([
            str(python), "-I", "-m", "orca_memory.codex_hook",
        ]) + ' "$@"\n',
    }
    for name, body in launchers.items():
        path = commands / name
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        path.chmod(0o700)

    hooks = json.loads((bundle / "hooks.template.json").read_text(encoding="utf-8"))
    for groups in hooks["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                hook["command"] = shlex.quote(str(commands / "orca-codex-hook"))
    (prefix / "hooks.json").write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")

    physical_skills = prefix / "skills"
    physical_skills.mkdir(mode=0o700)
    for name in SKILL_NAMES:
        target = physical_skills / name
        target.mkdir(mode=0o700)
        for relative, content in resources.items():
            if relative.startswith(name + "/"):
                path = target / relative.removeprefix(name + "/")
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with path.open("xb") as stream:
                    stream.write(content)

    skills_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in SKILL_NAMES:
        (skills_dir / name).symlink_to(physical_skills / name, target_is_directory=True)

    subprocess.run([str(commands / "orca"), "--help"], check=True, stdout=subprocess.DEVNULL)
    if create_vault:
        scaffold(bundle, vault)

    print(f"Installed: {prefix}\nHost configuration: {host_config}")
    print(f"Commands: {commands}\nHook to review: {prefix / 'hooks.json'}")
    print(f"Agent skills: {skills_dir} ({', '.join(SKILL_NAMES)} symlinks)")
    print("Configure the host before validation. No active hooks were changed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    bundle = Path(__file__).resolve().parent
    version = json.loads((bundle / "release.json").read_text())["version"]
    default_prefix = Path.home() / ".local/share/orca" / version
    parser.add_argument("--prefix", type=Path, default=default_prefix)
    parser.add_argument("--host-config", type=Path, default=None)
    parser.add_argument(
        "--vault-path", type=Path,
        help="Absolute path for a new or existing external Orca vault",
    )
    parser.add_argument(
        "--create-vault", action="store_true",
        help="Scaffold a new vault at --vault-path (never implied by binding)",
    )
    parser.add_argument(
        "--skills-dir", type=Path,
        default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "skills",
        help="Codex skills directory (default: CODEX_HOME/skills or ~/.codex/skills)",
    )
    args = parser.parse_args()
    if sys.platform != "linux" or sys.version_info < (3, 11):
        parser.error("This release requires Linux/WSL and Python 3.11 or newer")
    host_config = args.host_config or (args.prefix / "config/host.yaml")
    if args.create_vault and args.vault_path is None:
        parser.error("--create-vault requires --vault-path")
    try:
        install(
            bundle,
            args.prefix,
            host_config,
            args.skills_dir,
            vault_path=args.vault_path,
            create_vault=args.create_vault,
        )
    except (ValueError, OSError, KeyError, BadZipFile, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Installation stopped: {exc}\n")


if __name__ == "__main__":
    main()
