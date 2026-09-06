"""Build a checkout-independent WSL release into a new output directory."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tomllib


def build(output: Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    output = (output or root / "releases" / version).absolute()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    epoch = int(subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", revision], cwd=root, text=True,
    ).strip())
    build_env = {**os.environ, "SOURCE_DATE_EPOCH": str(epoch)}
    output.mkdir(parents=True, exist_ok=False)
    name = f"orca-memory-{version}-wsl"
    bundle = output / name
    bundle.mkdir()
    subprocess.run(["uv", "build", "--wheel", "--out-dir", str(bundle)],
                   cwd=root, env=build_env, check=True)
    subprocess.run([
        "uv", "export", "--locked", "--extra", "agentcairn", "--no-dev",
        "--no-emit-project", "--no-header", "--no-annotate",
        "--output-file", str(bundle / "requirements.txt"),
    ], cwd=root, check=True, stdout=subprocess.DEVNULL)
    wheel, = bundle.glob("*.whl")
    shutil.copyfile(root / "tools/install_release.py", bundle / "install.py")
    shutil.copyfile(root / "tools/scaffold_vault.py", bundle / "scaffold_vault.py")
    hooks = json.loads((root / "config/codex-hooks.user.example.json").read_text())
    for groups in hooks["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                hook["command"] = "@ORCA_INSTALLED_HOOK@"
    (bundle / "hooks.template.json").write_text(json.dumps(hooks, indent=2) + "\n")
    host = (root / "config/host.example.yaml").read_text().replace(
        "/workspace/projects/orca/.runtime", "/absolute/private/orca-runtime",
    )
    (bundle / "host.example.yaml").write_text(host)
    policy = (root / "config/orca-memory.example.yaml").read_text().replace(
        "replace-with-registered-adapter-id", "codex-cli",
    ).replace("replace-with-model-id", "gpt-5.6-luna")
    (bundle / "orca-memory.example.yaml").write_text(policy)
    setup = (root / "docs/operations/setup.md").read_text()
    readme = setup.split("<!-- release-guide:start -->\n", 1)[1].split(
        "<!-- release-guide:end -->", 1,
    )[0]
    (bundle / "README.md").write_text(readme)
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))
    manifest = {
        "version": version, "platform": "linux-wsl", "wheel": wheel.name,
        "source_revision": revision, "source_dirty": dirty,
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(bundle.iterdir())},
    }
    (bundle / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = output / f"{name}.tar.gz"
    def release_metadata(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = epoch
        info.mode = 0o755 if info.isdir() else 0o644
        info.pax_headers = {}
        return info

    with archive.open("wb") as output_stream:
        with gzip.GzipFile(filename="", fileobj=output_stream, mode="wb", mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as stream:
                stream.add(bundle, arcname=name, filter=release_metadata)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    print(archive)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="A new directory (default: releases/<version>)")
    build(parser.parse_args().output)
