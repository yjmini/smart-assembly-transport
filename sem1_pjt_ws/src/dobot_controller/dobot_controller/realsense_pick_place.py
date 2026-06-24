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

from dataclasses import dataclass, replace
from shlex import quote
from typing import Iterable, Any, Callable
import json
import subprocess
import threading
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
    upper_stack_place_lift_mm: float
    color_switch_settle_sec: float = 1.0
    quality_result: str = "normal"
    conveyor_sort_steps: int = 3200
    conveyor_step_delay_sec: float = 0.0001
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
            # 2026-06 hardware calibration: lower pickup 3 mm further after
            # the second smoke test.  Place car_lower close to the belt, then
            # place car_upper higher so it stacks on top of car_lower instead
            # of pressing down at the same conveyor Z.
            pick_z_mm=-50.0,
            conveyor_pose_mm=Pose4D(48.2, 196.3, 6.8, 0.0),
            conveyor_retreat_z_mm=70.0,
            object_place_spacing_y_mm=28.0,
            upper_stack_place_lift_mm=8.0,
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
        stack_lift_z = self.upper_stack_place_lift_mm if index >= 2 else 0.0
        return Pose4D(
            self.conveyor_pose_mm.x,
            self.conveyor_pose_mm.y + offset_y,
            self.conveyor_pose_mm.z + stack_lift_z,
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
        PickPlaceStep(f"{prefix}_move_above_conveyor", "dobot_pose", place_above),
        PickPlaceStep(f"{prefix}_descend_to_conveyor", "dobot_pose", place_pose),
        PickPlaceStep(f"{prefix}_release_on_conveyor", "suction", suction_enabled=False, dwell_sec=0.5),
        PickPlaceStep(f"{prefix}_retreat_from_conveyor", "dobot_pose", place_above),
    ]


def sort_action_for_quality(quality_result: str) -> tuple[str, str]:
    normalized = quality_result.strip().lower().replace("_", "-")
    if normalized in {"normal", "ok", "pass", "passed", "good", "left"}:
        return "sort-left", "sort_conveyor_left_after_quality_pass"
    if normalized in {"abnormal", "ng", "fail", "failed", "defect", "defective", "bad", "right"}:
        return "sort-right", "sort_conveyor_right_after_quality_fail"
    raise ValueError(f"Unsupported quality_result={quality_result!r}; expected normal/pass or abnormal/fail")


def build_conveyor_command(
    *,
    action: str,
    steps: int,
    step_delay_sec: float,
    host: str = "192.168.110.142",
    user: str = "ssafy",
) -> str:
    remote_env = {
        "CONVEYOR_MODE": "stepper",
        "CONVEYOR_GPIO_BACKEND": "gpiod",
        "CONVEYOR_STEP_PIN": "27",
        "CONVEYOR_DIR_PIN": "17",
        "CONVEYOR_ENABLE_PIN": "22",
        "CONVEYOR_ENABLE_ACTIVE_HIGH": "0",
        "CONVEYOR_DIR_ACTIVE_HIGH": "0",
        "CONVEYOR_STEPS": str(int(steps)),
        "CONVEYOR_STEP_DELAY_SEC": str(float(step_delay_sec)),
        "SORTER_SERVO_PIN": "18",
    }
    env = " ".join(f"{key}={quote(value)}" for key, value in remote_env.items())
    remote = f"{env} python3 ~/smart-assembly-transport-edge/conveyor_control.py {quote(action)}"
    return f"ssh {quote(user)}@{quote(host)} {quote(remote)}"


def build_two_object_pick_place_plan(points: Iterable[CameraPoint], config: PickPlaceConfig | None = None) -> PickPlacePlan:
    config = config or PickPlaceConfig.reference_from_project_pill()
    points = list(points)
    if len(points) != 2:
        raise ValueError(f"two-object pick/place requires exactly 2 RealSense target points; got {len(points)}")
    steps: list[PickPlaceStep] = []
    for index, point in enumerate(points, start=1):
        steps.extend(_steps_for_object(index, point, config))
    conveyor_action, step_name = sort_action_for_quality(config.quality_result)
    steps.append(PickPlaceStep(step_name, "conveyor", conveyor_action=conveyor_action))
    return PickPlacePlan(steps)


class ObjectPickPlaceCoordinator:
    """Runs long Dobot/conveyor work outside the ROS subscription callback.

    The ROS executor must remain free to process action-service responses while a
    pick/place cycle is running.  This coordinator accepts a target point quickly,
    starts the blocking work on a background thread, and rejects duplicate target
    messages until the current object is complete.
    """

    def __init__(
        self,
        config: PickPlaceConfig,
        execute_steps: Callable[[list[PickPlaceStep]], None],
        publish_status: Callable[[str], None],
        *,
        set_target_color: Callable[[str], None] | None = None,
        target_colors: tuple[str, ...] = ("car_lower", "car_upper"),
    ) -> None:
        self.config = config
        self.execute_steps = execute_steps
        self.publish_status = publish_status
        # The callback name is kept for backward compatibility; in YOLO mode the
        # published value is a class label such as car_lower/car_upper.
        self.set_target_color = set_target_color or (lambda _color: None)
        self.target_colors = tuple(color.strip().lower() for color in target_colors if color.strip()) or ("car_lower", "car_upper")
        self.completed_points: list[CameraPoint] = []
        self.executing = False
        self._ignore_targets_until = 0.0
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self.set_target_color(self.target_colors[0])

    @property
    def completed_count(self) -> int:
        with self._lock:
            return len(self.completed_points)

    def accept_target(self, point: CameraPoint) -> bool:
        with self._lock:
            if self.executing or len(self.completed_points) >= 2:
                return False
            if time.monotonic() < self._ignore_targets_until:
                return False
            self.executing = True
            object_index = len(self.completed_points) + 1
            self._worker = threading.Thread(
                target=self._run_object,
                args=(object_index, point),
                name=f"dobot_pick_place_object_{object_index}",
                daemon=True,
            )
            self._worker.start()
            return True

    def wait_for_idle(self, timeout_sec: float | None = None) -> None:
        worker = self._worker
        if worker is not None:
            worker.join(timeout=timeout_sec)

    def _run_object(self, object_index: int, point: CameraPoint) -> None:
        try:
            self.execute_steps(_steps_for_object(object_index, point, self.config))
            with self._lock:
                self.completed_points.append(point)
                completed = len(self.completed_points)
            if completed == 2:
                conveyor_action, step_name = sort_action_for_quality(self.config.quality_result)
                self.execute_steps([PickPlaceStep(step_name, "conveyor", conveyor_action=conveyor_action)])
                self.publish_status("COMPLETED_TWO_OBJECT_PICK_PLACE")
            else:
                next_color = self.target_colors[min(completed, len(self.target_colors) - 1)]
                self.set_target_color(next_color)
                with self._lock:
                    self._ignore_targets_until = time.monotonic() + self.config.color_switch_settle_sec
                self.publish_status("COMPLETED_OBJECT_1_WAITING_FOR_OBJECT_2")
        finally:
            with self._lock:
                self.executing = False


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
        quality_result = str(self.node.declare_parameter("quality_result", "normal").value)
        conveyor_sort_steps = int(self.node.declare_parameter("conveyor_sort_steps", 3200).value)
        conveyor_step_delay_sec = float(self.node.declare_parameter("conveyor_step_delay_sec", 0.0001).value)
        self.config = replace(
            PickPlaceConfig.reference_from_project_pill(),
            quality_result=quality_result,
            conveyor_sort_steps=conveyor_sort_steps,
            conveyor_step_delay_sec=conveyor_step_delay_sec,
        )
        self.motion_type = int(self.node.declare_parameter("motion_type", 1).value)
        target_colors_param = str(self.node.declare_parameter("target_colors", "car_lower,car_upper").value)
        # For compatibility with old launch files the parameter is still named
        # target_colors, but YOLO mode treats these values as class labels.
        self.target_colors = tuple(color.strip().lower() for color in target_colors_param.split(",") if color.strip()) or ("car_lower", "car_upper")
        self.ptp_action = str(self.node.declare_parameter("ptp_action", "PTP_action").value)
        self.conveyor_command_template = str(self.node.declare_parameter("conveyor_command", "").value)
        self.subscription = self.node.create_subscription(Point, "/target_pixel", self.target_callback, 10)
        self.status_pub = self.node.create_publisher(String, "/task_status", 10)
        self.plan_pub = self.node.create_publisher(String, "/dobot/two_object_plan", 10)
        self.target_color_pub = self.node.create_publisher(String, "/target_color", 10)
        self.action_client = ActionClient(self.node, PointToPoint, self.ptp_action)
        self.vacuum_client = self.node.create_client(SuctionCupControl, "/dobot_suction_cup_service")
        self.coordinator = ObjectPickPlaceCoordinator(
            self.config,
            self.execute_steps,
            self.publish_status,
            set_target_color=self.publish_target_color,
            target_colors=self.target_colors,
        )
        self.node.get_logger().info("Two-object RealSense→Dobot→Conveyor node ready; waiting for 2 target points")

    def target_callback(self, msg: Any) -> None:
        point = CameraPoint(float(msg.x), float(msg.y), float(msg.z))
        if point.z <= 0:
            self.node.get_logger().warn("Ignoring target point with non-positive depth")
            return
        object_index = self.coordinator.completed_count + 1
        accepted = self.coordinator.accept_target(point)
        if accepted:
            self.node.get_logger().info(
                f"Captured object {object_index}/2: camera=({point.x:.1f}, {point.y:.1f}, {point.z:.1f})"
            )
        else:
            self.node.get_logger().debug("Ignoring target point while object execution is already in progress")

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
                action = step.conveyor_action or "sort-left"
                command = self.conveyor_command_template.format(action=action) if self.conveyor_command_template else build_conveyor_command(
                    action=action,
                    steps=self.config.conveyor_sort_steps,
                    step_delay_sec=self.config.conveyor_step_delay_sec,
                )
                subprocess.run(command, shell=True, check=False, text=True, capture_output=True, timeout=60)

    def publish_status(self, status: str) -> None:
        from std_msgs.msg import String

        done = String()
        done.data = status
        self.status_pub.publish(done)

    def publish_target_color(self, color: str) -> None:
        from std_msgs.msg import String

        msg = String()
        msg.data = color
        self.target_color_pub.publish(msg)
        self.node.get_logger().info(f"Target detector value set to {color}")

    def send_pose_and_wait(self, target_pose: list[float]) -> None:
        goal_msg = self.PointToPoint.Goal()
        goal_msg.target_pose = [float(v) for v in target_pose]
        goal_msg.motion_type = self.motion_type
        self.node.get_logger().info(f"Waiting for Dobot action server {self.ptp_action}")
        if not self.action_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError(f"Dobot action server unavailable: {self.ptp_action}")
        future = self.action_client.send_goal_async(goal_msg)
        self._wait_for_future(future, timeout_sec=15.0, description="Dobot goal response")
        goal_handle = future.result()
        if not goal_handle or not goal_handle.accepted:
            raise RuntimeError(f"Dobot goal rejected: {target_pose}")
        result_future = goal_handle.get_result_async()
        self._wait_for_future(result_future, timeout_sec=60.0, description="Dobot goal result")

    @staticmethod
    def _wait_for_future(future: Any, timeout_sec: float, description: str) -> None:
        done = threading.Event()
        future.add_done_callback(lambda _future: done.set())
        if not done.wait(timeout=timeout_sec):
            raise TimeoutError(f"Timed out waiting for {description}")

    def set_vacuum(self, enable: bool) -> None:
        if not self.vacuum_client.wait_for_service(timeout_sec=2.0):
            self.node.get_logger().warn("Dobot suction service unavailable; continuing without vacuum confirmation")
            return
        request = self.SuctionCupControl.Request()
        request.enable_suction = enable
        future = self.vacuum_client.call_async(request)
        self._wait_for_future(future, timeout_sec=10.0, description="Dobot suction service response")

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
