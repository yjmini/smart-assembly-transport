"""Dobot real-action helpers built on the existing calibrated sequence."""
from __future__ import annotations

from dataclasses import dataclass
from shlex import quote
import json
import subprocess

try:
    from dobot_controller.sequence import AssemblyPoseConfig, AssemblyPlan, build_two_part_assembly_plan
    from hri_interfaces.ssh import CommandResult
except ImportError:
    from sem1_pjt_ws.src.dobot_controller.dobot_controller.sequence import AssemblyPoseConfig, AssemblyPlan, build_two_part_assembly_plan
    from sem1_pjt_ws.src.hri_interfaces.hri_interfaces.ssh import CommandResult


@dataclass(frozen=True)
class DobotExecutionPlan:
    action_name: str
    motion_type: int
    target_poses: list[list[float]]
    gripper_steps: list[str]

    def as_dashboard_payload(self) -> dict:
        return {"action_name": self.action_name, "motion_type": self.motion_type, "target_poses": self.target_poses, "gripper_steps": self.gripper_steps}


class DobotCommandBuilder:
    def __init__(self, action_name: str = "PTP_action", motion_type: int = 1) -> None:
        self.action_name = action_name
        self.motion_type = motion_type

    def action_command(self, target_pose: list[float]) -> list[str]:
        goal = json.dumps({"target_pose": target_pose, "motion_type": self.motion_type})
        return ["ros2", "action", "send_goal", self.action_name, "dobot_msgs/action/PointToPoint", goal]


class RealDobotController:
    def __init__(self, action_name: str = "PTP_action", motion_type: int = 1, *, execute: bool = False, timeout_sec: int = 60) -> None:
        self.builder = DobotCommandBuilder(action_name, motion_type)
        self.execute = execute
        self.timeout_sec = timeout_sec

    def run_pose(self, target_pose: list[float]) -> CommandResult:
        command = self.builder.action_command(target_pose)
        if not self.execute:
            return CommandResult(command=command, returncode=0, stdout="DRY_RUN", stderr="", executed=False)
        proc = subprocess.run(command, text=True, capture_output=True, timeout=self.timeout_sec, check=False)
        return CommandResult(command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, executed=True)


def build_real_dobot_execution_plan(action_name: str = "PTP_action", motion_type: int = 1, config: AssemblyPoseConfig | None = None) -> DobotExecutionPlan:
    plan: AssemblyPlan = build_two_part_assembly_plan(config or AssemblyPoseConfig.reference_default())
    return DobotExecutionPlan(action_name=action_name, motion_type=motion_type, target_poses=[step.pose.as_list() for step in plan.steps], gripper_steps=[step.gripper for step in plan.steps])
