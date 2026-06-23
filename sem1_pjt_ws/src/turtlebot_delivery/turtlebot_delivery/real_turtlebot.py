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

    def _goal_json(self, destination: str) -> str:
        pose = self.config.pose_for(destination)
        z, w = yaw_to_quaternion_z_w(pose.yaw)
        return json.dumps(
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

    def _nav2_goal_command(self, destination: str) -> str:
        goal = self._goal_json(destination)
        return f"ros2 action send_goal {quote(self.config.nav_action)} nav2_msgs/action/NavigateToPose {quote(goal)}"

    def _ssh_command(self, remote_steps: list[str]) -> list[str]:
        remote = " && ".join(
            [
                f"source {self._source_path(self.config.ros_setup)}",
                f"(source {self._source_path(self.config.workspace_setup)} || true)",
                f"export ROS_DOMAIN_ID={self.config.ros_domain_id}",
                *remote_steps,
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

    def navigate_command(self, destination: str) -> list[str]:
        return self._ssh_command([self._nav2_goal_command(destination)])

    def wait_command(self, dwell_sec: float = 3.0) -> list[str]:
        if dwell_sec < 0:
            raise ValueError("dwell_sec must be non-negative")
        return self._ssh_command([f"sleep {quote(format(dwell_sec, 'g'))}"])

    def delivery_round_trip_command(self, destination: str, dwell_sec: float = 3.0) -> list[str]:
        """Navigate to destination, wait there, then return to configured HOME.

        This command is intended for the post-loading step: once the completed
        assembly is on the TurtleBot, Nav2 drives to the user-selected map pose,
        waits for handoff/confirmation, and then drives back to the original
        HOME pose. `ros2 action send_goal` exits non-zero on failure, so the
        chained `&&` command does not continue to dwell/return if navigation
        fails.
        """
        if dwell_sec < 0:
            raise ValueError("dwell_sec must be non-negative")
        return self._ssh_command(
            [
                self._nav2_goal_command(destination),
                f"sleep {quote(format(dwell_sec, 'g'))}",
                self._nav2_goal_command(self.config.home_destination),
            ]
        )

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

    def wait_at_destination(self, dwell_sec: float = 3.0) -> CommandResult:
        return self.runner.run(self.builder.wait_command(dwell_sec))

    def delivery_round_trip(self, destination: str, dwell_sec: float = 3.0) -> CommandResult:
        return self.runner.run(self.builder.delivery_round_trip_command(destination, dwell_sec))

    def return_home(self) -> CommandResult:
        return self.runner.run(self.builder.return_home_command())

    def status(self) -> CommandResult:
        return self.runner.run(self.builder.status_command())
