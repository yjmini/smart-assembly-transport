"""RealSense D435i guided two-object Dobot pick/place workflow.

This module adapts the useful parts of the reference project at
`project_pill/robot_control_ws/src/picking_dobot/picking_dobot`:

- RealSense color + aligned depth produces a 3D point in camera coordinates.
- A calibrated 4x4 camera-to-Dobot transform maps that point to robot X/Y.
- Dobot executes an explicit safe-z pick/place sequence.
- After two objects are placed on the conveyor, the conveyor start command is
  triggered once.

The pure planning functions are dependency-free so they can be unit tested
without ROS 2 or Dobot hardware.  The `TwoObjectPickPlaceNode` ROS entrypoint is
loaded only at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any
import json
import subprocess
import time

try:
    from dobot_controller.sequence import Pose4D
except ImportError:
    from sem1_pjt_ws.src.dobot_controller.dobot_controller.sequence import Pose4D


@dataclass(frozen=True)
class CameraPoint:
    """3D point in RealSense camera coordinates, in millimetres."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class PickPlaceStep:
    name: str
    kind: str
    pose: Pose4D | None = None
    suction_enabled: bool | None = None
    conveyor_action: str | None = None
    dwell_sec: float = 0.0


@dataclass(frozen=True)
class PickPlacePlan:
    steps: list[PickPlaceStep]
    source: str = "realsense_d435i"

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "steps": [
                {
                    "name": step.name,
                    "kind": step.kind,
                    "pose": step.pose.as_list() if step.pose else None,
                    "suction_enabled": step.suction_enabled,
                    "conveyor_action": step.conveyor_action,
                    "dwell_sec": step.dwell_sec,
                }
                for step in self.steps
            ],
        }


@dataclass(frozen=True)
class PickPlaceConfig:
    transform_matrix: tuple[tuple[float, float, float, float], ...]
    safe_z_mm: float
    pick_z_mm: float
    conveyor_pose_mm: Pose4D
    conveyor_retreat_z_mm: float
    object_place_spacing_y_mm: float
    motion_r: float = 0.0

    @classmethod
    def reference_from_project_pill(cls) -> "PickPlaceConfig":
        """Reference values copied from project_pill's working control_node.py.

        The transform maps `[x_cam, y_cam, depth_z, 1]` to Dobot coordinates.
        The conveyor pose is the working `convayer_*` placement pose from the
        reference code.  These are starting calibration values; final millimetre
        offsets may still need small tuning on the real table.
        """

        return cls(
            transform_matrix=(
                (0.048553, 0.985575, 0.162123, 204.376144),
                (0.998327, -0.052987, 0.023133, -13.145106),
                (0.031390, 0.160728, -0.986499, 361.830566),
                (0.0, 0.0, 0.0, 1.0),
            ),
            safe_z_mm=70.0,
            pick_z_mm=-39.0,
            conveyor_pose_mm=Pose4D(48.2, 196.3, 17.8, 0.0),
            conveyor_retreat_z_mm=70.0,
            object_place_spacing_y_mm=28.0,
            motion_r=0.0,
        )

    def camera_to_robot_xy(self, point: CameraPoint) -> tuple[float, float]:
        vector = (float(point.x), float(point.y), float(point.z), 1.0)
        transformed = [sum(row[index] * vector[index] for index in range(4)) for row in self.transform_matrix]
        # project_pill compressed Y around the calibrated center for better real-table fit.
        center_y = -13.145106
        scale_ratio = 0.80
        corrected_x = transformed[0]
        corrected_y = center_y + (transformed[1] - center_y) * scale_ratio
        return corrected_x, corrected_y

    def conveyor_pose_for_index(self, index: int) -> Pose4D:
        offset_y = (index - 1) * self.object_place_spacing_y_mm
        return Pose4D(
            self.conveyor_pose_mm.x,
            self.conveyor_pose_mm.y + offset_y,
            self.conveyor_pose_mm.z,
            self.conveyor_pose_mm.r,
        )


def _pose_from_camera_point(point: CameraPoint, z_mm: float, config: PickPlaceConfig) -> Pose4D:
    x, y = config.camera_to_robot_xy(point)
    return Pose4D(x, y, z_mm, config.motion_r)


def _steps_for_object(index: int, point: CameraPoint, config: PickPlaceConfig) -> list[PickPlaceStep]:
    pick_above = _pose_from_camera_point(point, config.safe_z_mm, config)
    pick_pose = _pose_from_camera_point(point, config.pick_z_mm, config)
    place_pose = config.conveyor_pose_for_index(index)
    place_above = Pose4D(place_pose.x, place_pose.y, config.conveyor_retreat_z_mm, place_pose.r)
    prefix = f"object_{index}"
    return [
        PickPlaceStep(f"{prefix}_move_above_pick", "dobot_pose", pick_above),
        PickPlaceStep(f"{prefix}_descend_to_pick", "dobot_pose", pick_pose),
        PickPlaceStep(f"{prefix}_suction_on", "suction", suction_enabled=True, dwell_sec=0.5),
        PickPlaceStep(f"{prefix}_lift_after_pick", "dobot_pose", pick_above),
        PickPlaceStep(f"{prefix}_move_to_conveyor", "dobot_pose", place_above),
        PickPlaceStep(f"{prefix}_release_on_conveyor", "suction", suction_enabled=False, dwell_sec=0.5),
        PickPlaceStep(f"{prefix}_retreat_from_conveyor", "dobot_pose", place_above),
    ]


def build_two_object_pick_place_plan(points: Iterable[CameraPoint], config: PickPlaceConfig | None = None) -> PickPlacePlan:
    config = config or PickPlaceConfig.reference_from_project_pill()
    points = list(points)
    if len(points) != 2:
        raise ValueError(f"two-object pick/place requires exactly 2 RealSense target points; got {len(points)}")
    steps: list[PickPlaceStep] = []
    for index, point in enumerate(points, start=1):
        steps.extend(_steps_for_object(index, point, config))
    steps.append(PickPlaceStep("start_conveyor_after_two_objects", "conveyor", conveyor_action="start"))
    return PickPlacePlan(steps)


class TwoObjectPickPlaceNode:
    """ROS 2 node that waits for two RealSense points, picks both, then starts conveyor."""

    def __init__(self) -> None:
        import rclpy
        from rclpy.action import ActionClient
        from rclpy.node import Node
        from geometry_msgs.msg import Point
        from std_msgs.msg import String
        from dobot_msgs.action import PointToPoint
        from dobot_msgs.srv import SuctionCupControl

        class _Node(Node):
            pass

        self.node = _Node("two_object_pick_place_node")
        self.PointToPoint = PointToPoint
        self.SuctionCupControl = SuctionCupControl
        self.config = PickPlaceConfig.reference_from_project_pill()
        self.completed_points: list[CameraPoint] = []
        self.executing = False
        self.motion_type = int(self.node.declare_parameter("motion_type", 1).value)
        self.ptp_action = str(self.node.declare_parameter("ptp_action", "PTP_action").value)
        self.conveyor_command = str(
            self.node.declare_parameter(
                "conveyor_command",
                "ssh ssafy@192.168.110.142 'CONVEYOR_MODE=stepper CONVEYOR_GPIO_BACKEND=gpiod CONVEYOR_STEP_PIN=27 CONVEYOR_DIR_PIN=17 CONVEYOR_ENABLE_PIN=22 CONVEYOR_ENABLE_ACTIVE_HIGH=0 CONVEYOR_DIR_ACTIVE_HIGH=0 CONVEYOR_STEPS=800 CONVEYOR_STEP_DELAY_SEC=0.0001 python3 ~/smart-assembly-transport-edge/conveyor_control.py start'",
            ).value
        )
        self.subscription = self.node.create_subscription(Point, "/target_pixel", self.target_callback, 10)
        self.status_pub = self.node.create_publisher(String, "/task_status", 10)
        self.plan_pub = self.node.create_publisher(String, "/dobot/two_object_plan", 10)
        self.action_client = ActionClient(self.node, PointToPoint, self.ptp_action)
        self.vacuum_client = self.node.create_client(SuctionCupControl, "/dobot_suction_cup_service")
        self.node.get_logger().info("Two-object RealSense→Dobot→Conveyor node ready; waiting for 2 target points")

    def target_callback(self, msg: Any) -> None:
        if self.executing:
            return
        if len(self.completed_points) >= 2:
            return
        point = CameraPoint(float(msg.x), float(msg.y), float(msg.z))
        if point.z <= 0:
            self.node.get_logger().warn("Ignoring target point with non-positive depth")
            return
        object_index = len(self.completed_points) + 1
        self.node.get_logger().info(
            f"Captured object {object_index}/2: camera=({point.x:.1f}, {point.y:.1f}, {point.z:.1f})"
        )
        self.executing = True
        try:
            self.execute_steps(_steps_for_object(object_index, point, self.config))
            self.completed_points.append(point)
            if len(self.completed_points) == 2:
                self.execute_steps([PickPlaceStep("start_conveyor_after_two_objects", "conveyor", conveyor_action="start")])
                self.publish_status("COMPLETED_TWO_OBJECT_PICK_PLACE")
            else:
                self.publish_status("COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2")
        finally:
            self.executing = False

    def execute_plan(self, plan: PickPlacePlan) -> None:
        self.execute_steps(plan.steps)
        self.publish_status("COMPLETED_TWO_OBJECT_PICK_PLACE")

    def execute_steps(self, steps: list[PickPlaceStep]) -> None:
        from std_msgs.msg import String

        msg = String()
        msg.data = json.dumps(PickPlacePlan(steps).as_dict(), ensure_ascii=False)
        self.plan_pub.publish(msg)
        for step in steps:
            self.node.get_logger().info(f"Executing {step.name}")
            if step.kind == "dobot_pose" and step.pose is not None:
                self.send_pose_and_wait(step.pose.as_list())
            elif step.kind == "suction":
                self.set_vacuum(bool(step.suction_enabled))
                if step.dwell_sec:
                    time.sleep(step.dwell_sec)
            elif step.kind == "conveyor":
                subprocess.run(self.conveyor_command, shell=True, check=False, text=True, capture_output=True, timeout=30)

    def publish_status(self, status: str) -> None:
        from std_msgs.msg import String

        done = String()
        done.data = status
        self.status_pub.publish(done)

    def send_pose_and_wait(self, target_pose: list[float]) -> None:
        goal_msg = self.PointToPoint.Goal()
        goal_msg.target_pose = [float(v) for v in target_pose]
        goal_msg.motion_type = self.motion_type
        self.action_client.wait_for_server()
        future = self.action_client.send_goal_async(goal_msg)
        import rclpy

        rclpy.spin_until_future_complete(self.node, future)
        goal_handle = future.result()
        if not goal_handle or not goal_handle.accepted:
            raise RuntimeError(f"Dobot goal rejected: {target_pose}")
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self.node, result_future)

    def set_vacuum(self, enable: bool) -> None:
        if not self.vacuum_client.wait_for_service(timeout_sec=2.0):
            self.node.get_logger().warn("Dobot suction service unavailable; continuing without vacuum confirmation")
            return
        request = self.SuctionCupControl.Request()
        request.enable_suction = enable
        future = self.vacuum_client.call_async(request)
        import rclpy

        rclpy.spin_until_future_complete(self.node, future)

    def destroy_node(self) -> None:
        self.node.destroy_node()


def main(args=None) -> None:
    import rclpy

    rclpy.init(args=args)
    wrapper = TwoObjectPickPlaceNode()
    try:
        rclpy.spin(wrapper.node)
    except KeyboardInterrupt:
        pass
    finally:
        wrapper.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
