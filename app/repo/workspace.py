import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WorkspaceResult:
    success: bool
    output: str


class WorkspaceManager:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def _run(self, args: list[str]) -> WorkspaceResult:
        completed = subprocess.run(
            args,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return WorkspaceResult(success=completed.returncode == 0, output=output.strip())

    def status(self) -> WorkspaceResult:
        return self._run(["git", "status", "--porcelain"])

    def create_branch(self, name: str) -> WorkspaceResult:
        return self._run(["git", "checkout", "-b", name])

    def apply_patch(self, patch_file: Path) -> WorkspaceResult:
        return self._run(["git", "apply", str(patch_file)])

    def commit(self, message: str) -> WorkspaceResult:
        return self._run(["git", "commit", "-am", message])

    def diff(self, path: Optional[str] = None) -> WorkspaceResult:
        args = ["git", "diff"]
        if path:
            args.append(path)
        return self._run(args)

    def remotes(self) -> WorkspaceResult:
        return self._run(["git", "remote", "-v"])

    def current_branch(self) -> WorkspaceResult:
        return self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
