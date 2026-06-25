import pytest

from sem1_pjt_ws.src.vision_detector.vision_detector.realsense_detector import (
    HsvRange,
    RealSenseIntrinsics,
    YoloDetection,
    build_vision_detections_message,
    draw_yolo_detections,
    deproject_pixel_to_camera_mm,
    detect_largest_colored_depth_point,
    detect_largest_colored_depth_point_by_color,
    detect_largest_yolo_depth_point,
    select_yolo_detection,
)


def test_deproject_pixel_to_camera_mm_uses_realsense_intrinsics():
    intrinsics = RealSenseIntrinsics(fx=600.0, fy=600.0, cx=320.0, cy=240.0)

    point = deproject_pixel_to_camera_mm(380, 210, 500.0, intrinsics)

    assert point == pytest.approx((50.0, -25.0, 500.0), abs=0.01)


def test_detect_largest_colored_depth_point_returns_3d_center():
    import cv2
    import numpy as np

    bgr = np.zeros((100, 120, 3), dtype=np.uint8)
    cv2.rectangle(bgr, (30, 20), (70, 60), (0, 255, 255), -1)
    depth = np.zeros((100, 120), dtype=np.uint16)
    depth[38:43, 48:53] = 400
    intrinsics = RealSenseIntrinsics(fx=400.0, fy=400.0, cx=60.0, cy=50.0)

    detection = detect_largest_colored_depth_point(
        bgr,
        depth,
        intrinsics,
        HsvRange(lower=(15, 100, 80), upper=(45, 255, 255)),
        min_area=500,
    )

    assert detection is not None
    assert detection.pixel == pytest.approx((50, 40), abs=2)
    assert detection.camera_point_mm == pytest.approx((-10.0, -10.0, 400.0), abs=3.0)
    assert detection.area > 1000


def test_red_target_color_uses_red_hue_wraparound_mask():
    import cv2
    import numpy as np

    bgr = np.zeros((100, 120, 3), dtype=np.uint8)
    cv2.rectangle(bgr, (30, 20), (70, 60), (0, 0, 255), -1)
    depth = np.zeros((100, 120), dtype=np.uint16)
    depth[38:43, 48:53] = 450
    intrinsics = RealSenseIntrinsics(fx=450.0, fy=450.0, cx=60.0, cy=50.0)

    detection = detect_largest_colored_depth_point_by_color(
        bgr,
        depth,
        intrinsics,
        "red",
        min_area=500,
    )

    assert detection is not None
    assert detection.pixel == pytest.approx((50, 40), abs=2)
    assert detection.camera_point_mm == pytest.approx((-10.0, -10.0, 450.0), abs=3.0)


def test_select_yolo_detection_filters_for_car_labels_and_confidence():
    detections = [
        YoloDetection("car_lower", 0.91, (10, 20, 80, 100)),
        YoloDetection("car_upper", 0.84, (100, 30, 150, 90)),
        YoloDetection("person", 0.99, (0, 0, 200, 200)),
        YoloDetection("car_lower", 0.10, (20, 20, 120, 120)),
    ]

    selected = select_yolo_detection(detections, ["car_lower"], min_confidence=0.35, min_area=500)

    assert selected is not None
    assert selected.label == "car_lower"
    assert selected.confidence == pytest.approx(0.91)
    assert selected.center_pixel == (45, 60)


def test_yolo_depth_detection_returns_center_3d_point_and_label():
    import numpy as np

    class FakeResults:
        names = {0: "car_lower", 1: "car_upper"}
        xyxy = [np.array([[20, 30, 80, 90, 0.88, 0]], dtype=np.float32)]

    class FakeYoloModel:
        names = FakeResults.names

        def __call__(self, _image):
            return FakeResults()

    bgr = np.zeros((120, 160, 3), dtype=np.uint8)
    depth = np.zeros((120, 160), dtype=np.uint16)
    depth[57:64, 47:54] = 500
    intrinsics = RealSenseIntrinsics(fx=500.0, fy=500.0, cx=80.0, cy=60.0)

    detection = detect_largest_yolo_depth_point(
        bgr,
        depth,
        intrinsics,
        FakeYoloModel(),
        ["car_lower", "car_upper"],
        min_confidence=0.35,
        min_area=500,
    )

    assert detection is not None
    assert detection.label == "car_lower"
    assert detection.confidence == pytest.approx(0.88, abs=0.001)
    assert detection.pixel == (50, 60)
    assert detection.camera_point_mm == pytest.approx((-30.0, 0.0, 500.0), abs=0.01)


def test_build_vision_detections_message_uses_dashboard_bbox_schema():
    detections = [YoloDetection("car_lower", 0.87654, (10, 20, 80, 100))]

    payload = build_vision_detections_message(detections, image_shape=(480, 640), stamp=123.4)

    assert payload["type"] == "vision.detections"
    assert payload["stamp"] == 123.4
    assert payload["detections"][0]["label"] == "car_lower"
    assert payload["detections"][0]["confidence"] == 0.8765
    assert payload["detections"][0]["bbox"] == {"x": 10.0, "y": 20.0, "w": 70.0, "h": 80.0}
    assert payload["detections"][0]["image_width"] == 640
    assert payload["detections"][0]["image_height"] == 480


def test_draw_yolo_detections_changes_pixels_inside_bbox():
    import numpy as np

    bgr = np.zeros((120, 160, 3), dtype=np.uint8)
    annotated = draw_yolo_detections(bgr, [YoloDetection("car_lower", 0.88, (20, 30, 80, 90))], target_label="car_lower")

    assert annotated.shape == bgr.shape
    assert annotated.sum() > 0
    assert annotated[28:34, 18:24].sum() > 0
