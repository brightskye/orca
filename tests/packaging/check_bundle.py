"""Smoke-check a real Orca release archive without using the checkout runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile


_FORBIDDEN_PARTS = frozenset({".local", "legacy", "private", "tests"})
_PYTHONPATH_KEYS = frozenset({"PYTHONHOME", "PYTHONPATH", "CODEX_HOME", "ORCA_HOST_CONFIG", "ORCA_VAULT_PATH"})
_SYNTHETIC_APP_CHECK = r'''
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys

from orca_memory.application import LocalOrcaApplication
from orca_memory.configuration import load_configuration
from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.processor import ContinuationSummary, ProcessingProposal
from orca_memory.retrieval import RecallRequest
from orca_memory.storage import MemoryScope


class Provider:
    name = "synthetic-release-smoke/1"

    def distill(self, request):
        return ProcessingProposal(ContinuationSummary(
            "Release smoke publication",
            "The installed package preserves deterministic release smoke content.",
        ))


def check(host, publish):
    configuration = load_configuration(
        host, environ={}, registered_provider_adapters={"codex-cli"}
    )
    app = LocalOrcaApplication(
        configuration,
        Provider(),
        clock=lambda: datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "bundle-smoke-run",
    )
    if publish:
        turns = tuple(
            NormalizedTurn(
                "codex-local", "bundle-smoke-conversation", turn_id, occurred,
                f"codex://bundle-smoke/{turn_id}", text,
                hashlib.sha256(text.encode()).hexdigest(),
            )
            for turn_id, occurred, text in (
                ("request", "2026-09-01T11:59:00Z", "Verify deterministic release smoke content."),
                ("response", "2026-09-01T12:00:00Z", "The release smoke content is ready."),
            )
        )
        result = app.process(
            ConversationBatch("codex-local", "bundle-smoke-conversation", turns),
            scope=MemoryScope("general", "general"),
        )
        if result.status != "success":
            raise RuntimeError(f"synthetic publication returned {result.status}")
        app.recover_and_rebuild()
    response = app.recall(
        RecallRequest(question="deterministic release smoke", scope="general")
    )
    if not any(
        item.authority == "noncanonical" and item.scope == "general"
        and "deterministic release smoke" in item.excerpt.lower()
        for item in response.results
    ):
        raise RuntimeError("scoped Recall did not return the synthetic noncanonical publication")


check(Path(sys.argv[1]), len(sys.argv) > 2 and sys.argv[2] == "publish")
'''


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run(command: list[str], *, cwd: Path, environment: dict[str, str], label: str) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr.strip() or result.stdout.strip())[-2000:]
        raise RuntimeError(f"{label} failed ({result.returncode}): {detail}")
    return result.stdout


def _clean_environment(home: Path) -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key in _PYTHONPATH_KEYS:
            environment.pop(key, None)
    environment["HOME"] = str(home)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _safe_extract(archive: Path, destination: Path) -> Path:
    """Extract a regular-file-only archive after checking every member name."""
    with tarfile.open(archive, mode="r:gz") as stream:
        members = stream.getmembers()
        _require(members, "release archive is empty")
        checked: list[tuple[tarfile.TarInfo, tuple[str, ...]]] = []
        seen: set[str] = set()
        roots: set[str] = set()
        for member in members:
            raw = member.name
            path = PurePosixPath(raw.rstrip("/"))
            if (
                not raw
                or "\\" in raw
                or path.is_absolute()
                or not path.parts
                or any(part in {"", ".", ".."} for part in path.parts)
                or path.as_posix() != raw.rstrip("/")
                or (raw.endswith("/") and not member.isdir())
                or (path.parts[0].endswith(":") and len(path.parts[0]) == 2)
            ):
                raise ValueError(f"release archive has an unsafe member: {raw!r}")
            canonical = path.as_posix()
            if canonical in seen:
                raise ValueError(f"release archive has a duplicate member: {canonical}")
            seen.add(canonical)
            roots.add(path.parts[0])
            if not (member.isdir() or member.isreg()):
                raise ValueError(f"release archive contains a non-regular member: {raw!r}")
            checked.append((member, path.parts))

        _require(len(roots) == 1, "release archive must contain one top-level bundle")
        root_name = next(iter(roots))
        _require(
            any(member.isdir() and parts == (root_name,) for member, parts in checked),
            "release archive is missing its top-level bundle directory",
        )
        root = destination / root_name
        destination_resolved = destination.resolve()
        for member, parts in sorted(checked, key=lambda item: (len(item[1]), item[1])):
            target = destination.joinpath(*parts)
            _require(
                target.resolve(strict=False).is_relative_to(destination_resolved),
                f"release archive member escapes extraction root: {member.name!r}",
            )
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = stream.extractfile(member)
            if source is None:
                raise ValueError(f"release archive member has no data: {member.name!r}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
        return root


def _load_manifest(bundle: Path) -> dict:
    try:
        manifest = json.loads((bundle / "release.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("release manifest is not valid JSON") from exc
    _require(isinstance(manifest, dict), "release manifest is not an object")
    files = manifest.get("files")
    _require(isinstance(files, dict) and files, "release manifest has no file hashes")
    actual = {path.name for path in bundle.iterdir()}
    _require(actual == set(files) | {"release.json"}, "release files do not match release.json")
    for name, digest in files.items():
        _require(
            isinstance(name, str)
            and name
            and Path(name).name == name
            and isinstance(digest, str)
            and len(digest) == 64,
            f"invalid release manifest entry: {name!r}",
        )
        path = bundle / name
        _require(path.is_file() and not path.is_symlink(), f"invalid release file: {name}")
        _require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"release checksum mismatch: {name}")
    wheel_name = manifest.get("wheel")
    _require(isinstance(wheel_name, str) and wheel_name in files and wheel_name.endswith(".whl"), "release wheel is missing")
    return manifest


def _source_resources(repo: Path) -> dict[str, bytes]:
    resources: dict[str, bytes] = {}
    for relative_root in (Path("skills"), Path("vault_template")):
        root = repo / "src/orca_memory" / relative_root
        _require(root.is_dir(), f"source resource directory is missing: {root}")
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            resources[f"orca_memory/{relative_root.as_posix()}/{relative}"] = path.read_bytes()
    return resources


def _check_wheel(bundle: Path, wheel: Path, repo: Path) -> None:
    resources = _source_resources(repo)
    try:
        with ZipFile(wheel) as archive:
            entries = archive.infolist()
            names = [entry.filename.rstrip("/") for entry in entries]
            _require(len(names) == len(set(names)), "wheel contains duplicate paths")
            for name in names:
                parts = PurePosixPath(name).parts
                _require(not _FORBIDDEN_PARTS.intersection(parts), f"wheel contains private/test artifact: {name}")
            wheel_names = set(names)
            for name, expected in resources.items():
                _require(name in wheel_names, f"wheel is missing resource: {name}")
                _require(archive.read(name) == expected, f"wheel resource differs from source: {name}")
            _require("orca_memory/__init__.py" in wheel_names, "wheel is missing the runtime package")
    except BadZipFile as exc:
        raise ValueError("release wheel is not a valid zip archive") from exc


def _regular(path: Path, label: str) -> None:
    _require(path.is_file() and not path.is_symlink(), f"{label} is not a regular file: {path}")


def _directory(path: Path, label: str) -> None:
    _require(path.is_dir() and not path.is_symlink(), f"{label} is not a real directory: {path}")


def _private_directory(path: Path, label: str) -> None:
    _directory(path, label)
    _require(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0, f"{label} is not private: {path}")


def _check_prefix(prefix: Path, manifest: dict, skills_dir: Path) -> Path:
    _private_directory(prefix / "runtime", "installed runtime")
    _private_directory(prefix / "cache/uv", "installed uv cache")
    _directory(prefix / "config", "installed config")
    _directory(prefix / "bin", "installed commands")
    _directory(prefix / "skills", "installed physical skills")
    _regular(prefix / "config/host.yaml", "installed host config")
    for name in ("orca", "orca-codex-hook"):
        command = prefix / "bin" / name
        _regular(command, f"installed {name}")
        _require(os.access(command, os.X_OK), f"installed {name} is not executable")

    package = prefix / "package"
    _directory(package, "installed package copy")
    expected_package = set(manifest["files"]) | {"release.json"}
    actual_package = {path.name for path in package.iterdir()}
    _require(actual_package == expected_package, "installed package copy is incomplete")
    for path in package.iterdir():
        _regular(path, "installed package member")

    env_python = prefix / "env/bin/python"
    _require(env_python.is_file() and os.access(env_python, os.X_OK), "installed environment has no Python")
    for skill in ("orca-conversation", "orca-wiki"):
        physical = prefix / "skills" / skill
        _directory(physical, f"physical skill {skill}")
        _regular(physical / "SKILL.md", f"physical skill {skill} contents")
        link = skills_dir / skill
        _require(link.is_symlink(), f"external skill discovery link is missing: {link}")
        _require(link.resolve() == physical.resolve(), f"external skill link points elsewhere: {link}")
    return env_python


def _yaml_scalar(value: Path | str) -> str:
    return json.dumps(str(value))


def _replace_host_fields(
    path: Path,
    *,
    host_id: str | None = None,
    vault_path: Path | None = None,
    rollout_store: Path | None = None,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    replacements = {
        "host_id": _yaml_scalar(host_id) if host_id is not None else None,
        "vault_path": _yaml_scalar(vault_path) if vault_path is not None else None,
        "rollout_store": _yaml_scalar(rollout_store) if rollout_store is not None else None,
    }
    found: set[str] = set()
    for index, line in enumerate(lines):
        stripped = line.strip()
        for field, value in replacements.items():
            if value is None or not stripped.startswith(f"{field}:"):
                continue
            if field == "rollout_store" and not line.startswith("    "):
                continue
            if field != "rollout_store" and line.startswith(" "):
                continue
            lines[index] = f"{line[:len(line) - len(line.lstrip())]}{field}: {value}"
            found.add(field)
            break
    for field, value in replacements.items():
        if value is not None:
            _require(field in found, f"generated host config is missing {field}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _snapshot(path: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for child in path.rglob("*"):
        if child.is_symlink():
            raise AssertionError(f"synthetic vault contains a symlink: {child}")
        if child.is_file():
            result[child.relative_to(path).as_posix()] = child.read_bytes()
    return result


def _run_cli_commands(
    orca: Path,
    *,
    cwd: Path,
    environment: dict[str, str],
    commands: tuple[str, ...],
    label: str,
) -> dict[str, str]:
    outputs = {}
    for command in commands:
        outputs[command] = _run(
            [str(orca), command],
            cwd=cwd,
            environment=environment,
            label=f"{label} orca {command}",
        )
    return outputs


def _run_synthetic_app_check(
    env_python: Path,
    host_config: Path,
    *,
    cwd: Path,
    environment: dict[str, str],
    publish: bool,
) -> None:
    command = [str(env_python), "-I", "-c", _SYNTHETIC_APP_CHECK, str(host_config)]
    if publish:
        command.append("publish")
    _run(
        command,
        cwd=cwd,
        environment=environment,
        label="synthetic publication and scoped Recall" if publish else "moved-vault scoped Recall",
    )


def _independence_probe(
    *,
    repo: Path,
    bundle: Path,
    prefix: Path,
    moved_vault: Path,
    source_folder: Path,
    cwd: Path,
    environment: dict[str, str],
    mask_source: bool,
) -> str:
    """Optionally run installed code after hiding source and extracted bundle."""
    bwrap = shutil.which("bwrap")
    orca = prefix / "bin/orca"
    if not mask_source:
        return "LIMITED: source masking disabled; PYTHONPATH was cleared for all installed commands"
    if bwrap is None:
        raise RuntimeError("--mask-source requires bwrap, but bwrap is unavailable")

    writable = (prefix, moved_vault, source_folder, cwd)
    command = [bwrap, "--die-with-parent", "--new-session", "--unshare-net", "--ro-bind", "/", "/"]
    command.extend(["--tmpfs", str(repo)])
    command.extend(["--tmpfs", str(bundle)])
    for path in writable:
        command.extend(["--bind", str(path), str(path)])
    command.extend(["--chdir", str(cwd), "--setenv", "PYTHONPATH", "", "--"])
    _run(
        [
            *command,
            str(prefix / "env/bin/python"),
            "-I",
            "-c",
            _SYNTHETIC_APP_CHECK,
            str(prefix / "config/host.yaml"),
        ],
        cwd=cwd,
        environment=environment,
        label="source-independence bwrap Recall probe",
    )
    later_vault = cwd / "later-vault"
    _run(
        [
            *command,
            str(prefix / "env/bin/python"),
            "-I",
            str(prefix / "package/scaffold_vault.py"),
            "--vault-path",
            str(later_vault),
        ],
        cwd=cwd,
        environment=environment,
        label="source-independence bwrap scaffolder probe",
    )
    _directory(later_vault, "masked scaffolder vault")
    _regular(later_vault / "AGENTS.md", "masked scaffolder starter rules")
    _regular(later_vault / "System/Orca Memory/orca-memory.yaml", "masked scaffolder policy")
    return "PASS: bwrap hid the checkout and extracted bundle for Recall and scaffolding"


def check(archive: Path, *, mask_source: bool = False) -> str:
    archive = archive.expanduser().absolute()
    _require(archive.is_file() and not archive.is_symlink(), f"artifact is not a regular file: {archive}")
    repo = Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix="orca-release-check-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        workspace.mkdir()
        home = root / "home"
        home.mkdir()
        source_folder = root / "synthetic-source"
        source_folder.mkdir()
        skills_dir = root / "codex-skills"
        moved_vault = root / "moved-vault"
        bundle = _safe_extract(archive, root / "extracted")
        manifest = _load_manifest(bundle)
        wheel = bundle / manifest["wheel"]
        _check_wheel(bundle, wheel, repo)

        prefix = root / "installation"
        environment = _clean_environment(home)
        _run(
            [
                sys.executable,
                str(bundle / "install.py"),
                "--prefix",
                str(prefix),
                "--skills-dir",
                str(skills_dir),
                "--vault-path",
                str(root / "vault"),
                "--create-vault",
            ],
            cwd=workspace,
            environment=environment,
            label="release installer",
        )
        vault = root / "vault"
        _directory(vault, "scaffolded vault")
        env_python = _check_prefix(prefix, manifest, skills_dir)
        imported = _run(
            [str(env_python), "-I", "-c", "import orca_memory; print(orca_memory.__file__)"],
            cwd=workspace,
            environment=environment,
            label="installed package import",
        ).strip()
        _require(imported and Path(imported).resolve().is_relative_to((prefix / "env").resolve()), "package imported outside installed environment")

        host_config = prefix / "config/host.yaml"
        _replace_host_fields(
            host_config,
            host_id="bundle-smoke-host",
            rollout_store=source_folder,
        )
        host_text = host_config.read_text(encoding="utf-8")
        _require("project_root_mappings: []" in host_text, "synthetic host unexpectedly has project mappings")
        orca = prefix / "bin/orca"
        _run_cli_commands(
            orca,
            cwd=workspace,
            environment=environment,
            commands=("validate", "health", "rebuild", "status"),
            label="installed",
        )

        marker = vault / "Inbox/Notes/bundle-smoke.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker_content = b"synthetic bundle smoke marker\n"
        marker.write_bytes(marker_content)
        _run_synthetic_app_check(
            env_python,
            host_config,
            cwd=workspace,
            environment=environment,
            publish=True,
        )
        before = _snapshot(vault)
        shutil.move(vault, moved_vault)
        _require(_snapshot(moved_vault) == before, "vault contents changed while moving the vault")
        _require((moved_vault / "Inbox/Notes/bundle-smoke.md").read_bytes() == marker_content, "vault marker was not preserved")
        _replace_host_fields(host_config, vault_path=moved_vault)
        _run_cli_commands(
            orca,
            cwd=workspace,
            environment=environment,
            commands=("validate", "rebuild"),
            label="moved-vault",
        )
        _run_synthetic_app_check(
            env_python,
            host_config,
            cwd=workspace,
            environment=environment,
            publish=False,
        )
        independence = _independence_probe(
            repo=repo,
            bundle=bundle,
            prefix=prefix,
            moved_vault=moved_vault,
            source_folder=source_folder,
            cwd=workspace,
            environment=environment,
            mask_source=mask_source,
        )
    return independence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="absolute path to a release .tar.gz")
    parser.add_argument(
        "--mask-source",
        action="store_true",
        help="also run bwrap probes with the checkout and extracted bundle hidden",
    )
    args = parser.parse_args(argv)
    try:
        limitation = check(args.artifact, mask_source=args.mask_source)
    except (AssertionError, OSError, RuntimeError, ValueError, BadZipFile, tarfile.TarError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: release archive extracted safely, installed, and validated")
    print(f"Source independence: {limitation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
