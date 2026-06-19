"""Small subprocess-backed SSH runner with dry-run support."""
from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    executed: bool


class SSHRunner:
    def __init__(self, execute: bool = False, timeout_sec: int = 10) -> None:
        self.execute = execute
        self.timeout_sec = timeout_sec

    def run(self, command: list[str]) -> CommandResult:
        if not self.execute:
            return CommandResult(command=command, returncode=0, stdout="DRY_RUN", stderr="", executed=False)
        proc = subprocess.run(command, text=True, capture_output=True, timeout=self.timeout_sec, check=False)
        return CommandResult(command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, executed=True)
