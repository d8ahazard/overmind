import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from app.core.tool_broker import ToolRequest, ToolResult


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


def is_destructive_command(command: Sequence[str] | str) -> bool:
    if isinstance(command, list):
        parts = [str(item) for item in command if item]
    else:
        parts = str(command).strip().split()
    if not parts:
        return False
    cmd = parts[0].lower()
    destructive = {"rm", "del", "erase", "rmdir", "rd"}
    if cmd in destructive:
        return True
    if cmd == "git":
        rest = " ".join(parts[1:]).lower()
        if "reset --hard" in rest or "clean -fdx" in rest or "clean -ffdx" in rest:
            return True
    return False


def execute_shell_tool(request: ToolRequest) -> ToolResult:
    command = request.arguments.get("command")
    cwd = request.arguments.get("cwd")
    allowed_roots = request.arguments.get("allowed_roots", [])
    if not command or not allowed_roots:
        return ToolResult(success=False, error="invalid_request")
    roots = [Path(root) for root in allowed_roots]
    try:
        result = run_command(command, cwd=Path(cwd), allowed_roots=roots)
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))
    return ToolResult(
        success=result.success,
        output={
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        },
    )


def system_info() -> dict:
    return {
        "os": os.name,
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
