"""Real hardware configuration shared by backend, ROS 2 nodes, and tests."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config" / "hardware.json"


@dataclass(frozen=True)
class ConveyorConfig:
    ssh_user: str
    host: str
    ssh_port: int = 22
    remote_python: str = "python3"
    remote_script: str = "~/smart-assembly-transport-edge/conveyor_control.py"
    start_args: tuple[str, ...] = ("start",)
    stop_args: tuple[str, ...] = ("stop",)
    emergency_stop_args: tuple[str, ...] = ("emergency-stop",)
    status_args: tuple[str, ...] = ("status",)
    connect_timeout_sec: int = 5

    @property
    def target(self) -> str:
        return f"{self.ssh_user}@{self.host}"


@dataclass(frozen=True)
class DeliveryPose:
    x: float
    y: float
    yaw: float


@dataclass(frozen=True)
class TurtleBotConfig:
    ssh_user: str
    host: str
    ssh_port: int = 22
    ros_domain_id: int = 34
    ros_setup: str = "/opt/ros/humble/setup.bash"
    workspace_setup: str = "~/turtlebot4_ws/install/setup.bash"
    nav_action: str = "/navigate_to_pose"
    map_frame: str = "map"
    targets: dict[str, DeliveryPose] | None = None
    connect_timeout_sec: int = 5

    @property
    def target(self) -> str:
        return f"{self.ssh_user}@{self.host}"

    def pose_for(self, destination: str) -> DeliveryPose:
        targets = self.targets or {}
        key = destination.upper()
        if key not in targets:
            raise ValueError(f"Unknown TurtleBot destination {destination!r}; configured={sorted(targets)}")
        return targets[key]


@dataclass(frozen=True)
class DobotConfig:
    mode: str = "ros2_action"
    ptp_action: str = "PTP_action"
    motion_type: int = 1
    safe_z_mm: float = 20.0
    pick_z_mm: float = -31.77


@dataclass(frozen=True)
class VisionConfig:
    camera_topic: str = "/camera/camera/color/image_raw"
    base_color: str = "yellow"
    min_area: float = 1000.0
    hand_color: str = "skin"


@dataclass(frozen=True)
class DashboardConfig:
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8765
    http_port: int = 3000


@dataclass(frozen=True)
class HardwareConfig:
    mode: str
    conveyor: ConveyorConfig
    turtlebot: TurtleBotConfig
    dobot: DobotConfig
    vision: VisionConfig
    dashboard: DashboardConfig

    @classmethod
    def load(cls, path: str | Path = DEFAULT_CONFIG_PATH) -> "HardwareConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        turtle = dict(data["turtlebot"])
        turtle["targets"] = {name: DeliveryPose(**pose) for name, pose in turtle.get("targets", {}).items()}
        return cls(
            mode=data.get("mode", "real"),
            conveyor=ConveyorConfig(**data["conveyor"]),
            turtlebot=TurtleBotConfig(**turtle),
            dobot=DobotConfig(**data.get("dobot", {})),
            vision=VisionConfig(**data.get("vision", {})),
            dashboard=DashboardConfig(**data.get("dashboard", {})),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "conveyor": {"target": self.conveyor.target, "host": self.conveyor.host, "ssh_port": self.conveyor.ssh_port},
            "turtlebot": {
                "target": self.turtlebot.target,
                "host": self.turtlebot.host,
                "ssh_port": self.turtlebot.ssh_port,
                "ros_domain_id": self.turtlebot.ros_domain_id,
                "targets": {k: vars(v) for k, v in (self.turtlebot.targets or {}).items()},
            },
            "dobot": vars(self.dobot),
            "vision": vars(self.vision),
            "dashboard": vars(self.dashboard),
        }
