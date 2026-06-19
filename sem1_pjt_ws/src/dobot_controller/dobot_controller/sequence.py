"""Mock/real-compatible Dobot assembly sequence builder."""
from __future__ import annotations

from dataclasses import dataclass

from .calibration import PixelToRobotCalibrator


@dataclass(frozen=True)
class Pose4D:
    x: float
    y: float
    z: float
    r: float = 0.0

    def as_list(self) -> list[float]:
        return [float(self.x), float(self.y), float(self.z), float(self.r)]


@dataclass(frozen=True)
class DobotStep:
    name: str
    pose: Pose4D
    gripper: str = "hold"
    dwell_sec: float = 0.0


@dataclass(frozen=True)
class AssemblyPoseConfig:
    safe_z_mm: float
    pick_z_mm: float
    part_a_pixel: tuple[float, float]
    part_b_pixel: tuple[float, float]
    conveyor_place_pose_mm: Pose4D
    stack_offset_mm: tuple[float, float, float]
    calibrator: PixelToRobotCalibrator

    @classmethod
    def reference_default(cls) -> "AssemblyPoseConfig":
        return cls(
            safe_z_mm=20.0,
            pick_z_mm=-31.77,
            part_a_pixel=(320.0, 240.0),
            part_b_pixel=(390.0, 240.0),
            conveyor_place_pose_mm=Pose4D(220.0, 0.0, -25.0, 0.0),
            stack_offset_mm=(0.0, 0.0, 18.0),
            calibrator=PixelToRobotCalibrator.reference_default(),
        )


@dataclass(frozen=True)
class AssemblyPlan:
    steps: list[DobotStep]
    placeholder_fields: list[str]


def _pixel_pose(pixel: tuple[float, float], z: float, calibrator: PixelToRobotCalibrator) -> Pose4D:
    x, y = calibrator.pixel_to_robot(*pixel)
    return Pose4D(x=x, y=y, z=z, r=0.0)


def build_two_part_assembly_plan(config: AssemblyPoseConfig) -> AssemblyPlan:
    a_above = _pixel_pose(config.part_a_pixel, config.safe_z_mm, config.calibrator)
    a_pick = _pixel_pose(config.part_a_pixel, config.pick_z_mm, config.calibrator)
    b_above = _pixel_pose(config.part_b_pixel, config.safe_z_mm, config.calibrator)
    b_pick = _pixel_pose(config.part_b_pixel, config.pick_z_mm, config.calibrator)
    place = config.conveyor_place_pose_mm
    stack = Pose4D(place.x + config.stack_offset_mm[0], place.y + config.stack_offset_mm[1], place.z + config.stack_offset_mm[2], place.r)
    steps = [
        DobotStep("move_above_part_a", a_above, "open"),
        DobotStep("pick_part_a", a_pick, "close", 0.5),
        DobotStep("lift_part_a", a_above, "close"),
        DobotStep("place_part_a_on_conveyor", place, "open", 0.5),
        DobotStep("move_above_part_b", b_above, "open"),
        DobotStep("pick_part_b", b_pick, "close", 0.5),
        DobotStep("lift_part_b", b_above, "close"),
        DobotStep("stack_part_b_on_part_a", stack, "open", 0.5),
        DobotStep("retreat_safe_home", Pose4D(200.0, 0.0, config.safe_z_mm, 0.0), "open"),
    ]
    return AssemblyPlan(steps=steps, placeholder_fields=["safe_z_mm", "pick_z_mm", "part_a_pixel", "part_b_pixel", "conveyor_place_pose_mm", "stack_offset_mm"])
