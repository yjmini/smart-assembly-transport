"""TurtleBot4 SSH/Nav2 adapter using ROS_DOMAIN_ID=34."""
from __future__ import annotations

from dataclasses import dataclass
from math import sin, cos
from shlex import quote
import json

try:
    from hri_interfaces.hardware_config import TurtleBotConfig
    from hri_interfaces.ssh import CommandResult, SSHRunner
except ImportError:
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.hardware_config import TurtleBotConfig
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.ssh import CommandResult, SSHRunner


def yaw_to_quaternion_z_w(yaw: float) -> tuple[float, float]:
    return sin(yaw / 2.0), cos(yaw / 2.0)


@dataclass(frozen=True)
class TurtleBotCommandBuilder:
    config: TurtleBotConfig

    @staticmethod
    def _source_path(path: str) -> str:
        return path if path.startswith("~/") else quote(path)

    def navigate_command(self, destination: str) -> list[str]:
        pose = self.config.pose_for(destination)
        z, w = yaw_to_quaternion_z_w(pose.yaw)
        goal = json.dumps(
            {
                "pose": {
                    "header": {"frame_id": self.config.map_frame},
                    "pose": {
                        "position": {"x": pose.x, "y": pose.y, "z": 0.0},
                        "orientation": {"z": z, "w": w},
                    },
                }
            }
        )
        remote = " && ".join(
            [
                f"source {self._source_path(self.config.ros_setup)}",
                f"source {self._source_path(self.config.workspace_setup)} || true",
                f"export ROS_DOMAIN_ID={self.config.ros_domain_id}",
                f"ros2 action send_goal {quote(self.config.nav_action)} nav2_msgs/action/NavigateToPose {quote(goal)}",
            ]
        )
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

    def status_command(self) -> list[str]:
        remote = " && ".join(
            [
                f"source {self._source_path(self.config.ros_setup)}",
                f"export ROS_DOMAIN_ID={self.config.ros_domain_id}",
                "ros2 node list | head -50",
            ]
        )
        return ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={self.config.connect_timeout_sec}", "-p", str(self.config.ssh_port), self.config.target, remote]

    def return_home_command(self) -> list[str]:
        return self.navigate_command(self.config.home_destination)


class RealTurtleBotDelivery:
    def __init__(self, config: TurtleBotConfig, *, execute: bool = False) -> None:
        self.builder = TurtleBotCommandBuilder(config)
        self.runner = SSHRunner(execute=execute, timeout_sec=config.connect_timeout_sec + 120)

    def navigate(self, destination: str) -> CommandResult:
        return self.runner.run(self.builder.navigate_command(destination))

    def return_home(self) -> CommandResult:
        return self.runner.run(self.builder.return_home_command())

    def status(self) -> CommandResult:
        return self.runner.run(self.builder.status_command())
