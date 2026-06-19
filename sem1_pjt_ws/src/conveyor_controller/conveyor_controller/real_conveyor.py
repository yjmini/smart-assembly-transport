"""Raspberry Pi backed conveyor adapter.

The project PC controls the conveyor Pi via SSH.  The Pi is expected to expose a
small `conveyor_control.py` script with start/stop/emergency-stop/status
subcommands.  `scripts/edge/conveyor_control.py` provides a template for that
remote side.
"""
from __future__ import annotations

from dataclasses import dataclass
from shlex import quote

try:
    from hri_interfaces.hardware_config import ConveyorConfig
    from hri_interfaces.ssh import CommandResult, SSHRunner
except ImportError:
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import ConveyorConfig
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.ssh import CommandResult, SSHRunner


@dataclass(frozen=True)
class ConveyorCommandBuilder:
    config: ConveyorConfig

    def ssh_command(self, action: str) -> list[str]:
        action_args = {
            "start": self.config.start_args,
            "stop": self.config.stop_args,
            "emergency-stop": self.config.emergency_stop_args,
            "status": self.config.status_args,
        }[action]
        script = self.config.remote_script if self.config.remote_script.startswith("~/") else quote(self.config.remote_script)
        remote = " ".join([quote(self.config.remote_python), script, *map(quote, action_args)])
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self.config.connect_timeout_sec}",
            "-p",
            str(self.config.ssh_port),
            self.config.target,
            remote,
        ]


class RealConveyorController:
    def __init__(self, config: ConveyorConfig, *, execute: bool = False) -> None:
        self.builder = ConveyorCommandBuilder(config)
        self.runner = SSHRunner(execute=execute, timeout_sec=config.connect_timeout_sec + 10)

    def start(self) -> CommandResult:
        return self.runner.run(self.builder.ssh_command("start"))

    def stop(self) -> CommandResult:
        return self.runner.run(self.builder.ssh_command("stop"))

    def emergency_stop(self) -> CommandResult:
        return self.runner.run(self.builder.ssh_command("emergency-stop"))

    def status(self) -> CommandResult:
        return self.runner.run(self.builder.ssh_command("status"))
