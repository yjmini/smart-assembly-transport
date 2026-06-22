"""RealSense D435i color + depth object detector.

The ROS node follows the reference project pattern: subscribe to color image,
aligned depth image, and camera_info; threshold a target color in HSV; publish a
`geometry_msgs/Point` containing camera-frame 3D coordinates in millimetres.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RealSenseIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float


@dataclass(frozen=True)
class HsvRange:
    lower: tuple[int, int, int]
    upper: tuple[int, int, int]


@dataclass(frozen=True)
class DepthDetection:
    pixel: tuple[int, int]
    camera_point_mm: tuple[float, float, float]
    area: float


HSV_RANGES = {
    "yellow": HsvRange((15, 100, 80), (45, 255, 255)),
    "blue": HsvRange((100, 150, 80), (130, 255, 255)),
    "green": HsvRange((40, 100, 80), (80, 255, 255)),
}


def deproject_pixel_to_camera_mm(u: int, v: int, depth_mm: float, intrinsics: RealSenseIntrinsics) -> tuple[float, float, float]:
    x = (float(u) - intrinsics.cx) * float(depth_mm) / intrinsics.fx
    y = (float(v) - intrinsics.cy) * float(depth_mm) / intrinsics.fy
    return x, y, float(depth_mm)


def red_mask(hsv_image: Any):
    import cv2
    import numpy as np

    mask1 = cv2.inRange(hsv_image, np.array([0, 150, 80]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv_image, np.array([170, 150, 80]), np.array([179, 255, 255]))
    return cv2.bitwise_or(mask1, mask2)


def mask_for_hsv_range(hsv_image: Any, hsv_range: HsvRange):
    import cv2
    import numpy as np

    return cv2.inRange(hsv_image, np.array(hsv_range.lower), np.array(hsv_range.upper))


def median_depth_near_pixel(depth_image: Any, u: int, v: int, *, radius: int = 2) -> float:
    height, width = depth_image.shape
    u_min, u_max = max(0, u - radius), min(width, u + radius + 1)
    v_min, v_max = max(0, v - radius), min(height, v + radius + 1)
    roi = depth_image[v_min:v_max, u_min:u_max]
    valid_depths = roi[roi > 0]
    if len(valid_depths) == 0:
        return 0.0
    import numpy as np

    return float(np.median(valid_depths))


def detect_largest_colored_depth_point(
    bgr_image: Any,
    depth_image: Any,
    intrinsics: RealSenseIntrinsics,
    hsv_range: HsvRange,
    *,
    min_area: float = 1000.0,
) -> DepthDetection | None:
    import cv2
    import numpy as np

    hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    mask = mask_for_hsv_range(hsv_image, hsv_range)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = [contour for contour in contours if cv2.contourArea(contour) >= min_area]
    if not candidates:
        return None
    contour = max(candidates, key=cv2.contourArea)
    rect = cv2.minAreaRect(contour)
    u, v = int(rect[0][0]), int(rect[0][1])
    depth_mm = median_depth_near_pixel(depth_image, u, v)
    if depth_mm <= 0:
        return None
    return DepthDetection(
        pixel=(u, v),
        camera_point_mm=deproject_pixel_to_camera_mm(u, v, depth_mm, intrinsics),
        area=float(cv2.contourArea(contour)),
    )


class RealSenseObjectDetectorNode:
    def __init__(self) -> None:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Image, CameraInfo
        from geometry_msgs.msg import Point
        from std_msgs.msg import String
        from cv_bridge import CvBridge

        class _Node(Node):
            pass

        self.node = _Node("realsense_object_detector")
        self.bridge = CvBridge()
        self.Point = Point
        self.target_color = str(self.node.declare_parameter("target_color", "yellow").value)
        self.min_area = float(self.node.declare_parameter("min_area", 1000.0).value)
        self.depth_image = None
        self.intrinsics: RealSenseIntrinsics | None = None
        self.publisher = self.node.create_publisher(Point, "/target_pixel", 10)
        self.color_sub = self.node.create_subscription(String, "/target_color", self.color_callback, 10)
        self.image_sub = self.node.create_subscription(Image, "/camera/camera/color/image_raw", self.image_callback, qos_profile_sensor_data)
        self.depth_sub = self.node.create_subscription(Image, "/camera/camera/aligned_depth_to_color/image_raw", self.depth_callback, qos_profile_sensor_data)
        self.info_sub = self.node.create_subscription(CameraInfo, "/camera/camera/color/camera_info", self.info_callback, qos_profile_sensor_data)
        self.node.get_logger().info("RealSense D435i object detector ready; publishing /target_pixel")

    def color_callback(self, msg: Any) -> None:
        self.target_color = msg.data.strip().lower()
        self.node.get_logger().info(f"Target color changed to {self.target_color}")

    def info_callback(self, msg: Any) -> None:
        self.intrinsics = RealSenseIntrinsics(fx=msg.k[0], fy=msg.k[4], cx=msg.k[2], cy=msg.k[5])

    def depth_callback(self, msg: Any) -> None:
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as exc:  # noqa: BLE001
            self.node.get_logger().error(f"Depth conversion failed: {exc}")

    def image_callback(self, msg: Any) -> None:
        if self.depth_image is None or self.intrinsics is None:
            return
        if self.target_color == "none":
            return
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:  # noqa: BLE001
            self.node.get_logger().error(f"Color conversion failed: {exc}")
            return
        hsv_range = HSV_RANGES.get(self.target_color, HSV_RANGES["yellow"])
        detection = detect_largest_colored_depth_point(bgr, self.depth_image, self.intrinsics, hsv_range, min_area=self.min_area)
        if not detection:
            return
        point_msg = self.Point()
        point_msg.x, point_msg.y, point_msg.z = detection.camera_point_mm
        self.publisher.publish(point_msg)

    def destroy_node(self) -> None:
        self.node.destroy_node()


def main(args=None) -> None:
    import rclpy

    rclpy.init(args=args)
    wrapper = RealSenseObjectDetectorNode()
    try:
        rclpy.spin(wrapper.node)
    except KeyboardInterrupt:
        pass
    finally:
        wrapper.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
