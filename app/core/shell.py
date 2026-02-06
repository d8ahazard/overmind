import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass
class ShellResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def run_command(
    command: Sequence[str] | str,
    cwd: Path,
    allowed_roots: List[Path],
    env: Optional[dict] = None,
) -> ShellResult:
    if not any(_is_within(cwd, root) for root in allowed_roots):
        raise ValueError("Command cwd is outside allowed roots.")

    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        shell=isinstance(command, str),
        check=False,
    )
    return ShellResult(
        success=completed.returncode == 0,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        exit_code=completed.returncode,
    )


def system_info() -> dict:
    return {
        "os": os.name,
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
