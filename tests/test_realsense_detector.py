import pytest

from sem1_pjt_ws.src.vision_detector.vision_detector.realsense_detector import (
    HsvRange,
    RealSenseIntrinsics,
    deproject_pixel_to_camera_mm,
    detect_largest_colored_depth_point,
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
