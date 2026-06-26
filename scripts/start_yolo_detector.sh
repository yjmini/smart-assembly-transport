#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-34}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
ROS_DISTRO_NAME="${ROS_DISTRO:-humble}"
ROS_SETUP="/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
if [ -f "$ROS_SETUP" ]; then
  set +u
  # shellcheck disable=SC1090
  source "$ROS_SETUP"
  set -u
fi
if [ -f "sem1_pjt_ws/install/setup.bash" ]; then
  set +u
  # shellcheck disable=SC1091
  source sem1_pjt_ws/install/setup.bash
  set -u
fi

exec ros2 run vision_detector realsense_object_detector --ros-args \
  -p detector_mode:="${YOLO_DETECTOR_MODE:-yolo}" \
  -p yolo_model_path:="${YOLO_MODEL_PATH:-/home/ssafy/smart-assembly-transport/models/yolo/car_parts_best.pt}" \
  -p target_labels:="${YOLO_TARGET_LABELS:-car_lower,car_upper}" \
  -p min_confidence:="${YOLO_MIN_CONFIDENCE:-0.35}" \
  -p min_area:="${YOLO_MIN_AREA:-1000.0}" \
  -p yolo_roi:="${YOLO_ROI:-0.161,0.0,0.611,0.599}"
