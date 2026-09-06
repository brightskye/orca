"""Small Linux process boundary for the qualified Codex semantic provider.

Only the static Codex executable, TLS/DNS files, one authentication file, and
the current disposable work directory enter the sandbox. No user configuration,
checkout, vault, rollout store, shell, plugin, or code-mode host is mounted.
"""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import shutil
import subprocess


QUALIFIED_CODEX_VERSION = "codex-cli 0.153.4"
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "code_mode", "code_mode_host", "multi_agent",
    "multi_agent_v2", "apps", "plugins", "remote_plugin", "browser_use",
    "browser_use_external", "computer_use", "image_generation", "view_image",
    "memories", "hooks", "goals", "sleep_tool", "tool_suggest", "skill_search",
    "workspace_dependencies", "shell_snapshot",
)


class CodexIsolationError(RuntimeError):
    """The qualified provider boundary is unavailable; never fall back."""


def isolated_command(command: list[str], workspace: Path) -> tuple[list[str], dict[str, str]]:
    """Wrap a Codex command without inheriting the host environment or filesystem.

    File-backed Codex authentication and bubblewrap are required. Unsupported
    executable versions fail before a semantic call and require requalification.
    """

    executable = shutil.which(command[0])
    bubblewrap = shutil.which("bwrap")
    if not executable or not bubblewrap:
        raise CodexIsolationError("Codex provider requires Codex and bubblewrap")
    binary = Path(executable).resolve(strict=True)
    info = binary.stat()
    _check_version(str(binary), info.st_mtime_ns, info.st_size)
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    auth = codex_home / "auth.json"
    if not auth.is_file():
        raise CodexIsolationError("Codex provider requires local file-backed authentication")
    auth = auth.resolve(strict=True)
    workspace = workspace.resolve(strict=True)
    wrapped = [
        bubblewrap, "--die-with-parent", "--new-session", "--unshare-user",
        "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--clearenv",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--dir", "/usr/bin", "--ro-bind", str(binary), "/usr/bin/codex",
        "--dir", "/home/orca/.codex",
        "--ro-bind", str(auth), "/home/orca/.codex/auth.json",
        "--bind", str(workspace), str(workspace),
        "--chdir", str(workspace),
        "--setenv", "HOME", "/home/orca",
        "--setenv", "CODEX_HOME", "/home/orca/.codex",
        "--setenv", "PATH", "/usr/bin",
        "--setenv", "LANG", "C.UTF-8",
    ]
    for source in ("/etc/resolv.conf", "/etc/hosts", "/etc/ssl/certs/ca-certificates.crt"):
        path = Path(source)
        if path.is_file():
            wrapped.extend(("--ro-bind", str(path.resolve()), source))
    # Preserve command paths inside the one mounted workspace for schema/output.
    wrapped.extend(("--", "/usr/bin/codex", *command[1:]))
    return wrapped, {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}


@lru_cache(maxsize=4)
def _check_version(binary: str, mtime_ns: int, size: int) -> None:
    try:
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10,
            check=False, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CodexIsolationError("Codex provider executable qualification failed") from exc
    if result.returncode != 0 or result.stdout.strip() != QUALIFIED_CODEX_VERSION:
        raise CodexIsolationError("Codex provider version requires isolation requalification")
