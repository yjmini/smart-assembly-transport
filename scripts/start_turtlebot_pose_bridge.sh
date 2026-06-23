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

exec /usr/bin/python3 scripts/turtlebot_pose_ws_bridge.py \
  --topic "${TURTLEBOT_POSE_TOPIC:-/amcl_pose}" \
  --message-type "${TURTLEBOT_POSE_TYPE:-amcl}" \
  --ws-url "${DASHBOARD_WS_URL:-ws://127.0.0.1:8765}" \
  --rate-hz "${TURTLEBOT_POSE_RATE_HZ:-10}"
