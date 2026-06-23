#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-34}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
# Do not disable Fast DDS shared memory by default: the RealSense camera node on
# this workstation can publish frames even while FastDDS prints SHM lock warnings.
# Force UDP-only only when explicitly needed:
#   USE_FASTDDS_NO_SHM=1 scripts/start_realsense_stream.sh
if [ "${USE_FASTDDS_NO_SHM:-0}" = "1" ]; then
  export FASTRTPS_DEFAULT_PROFILES_FILE="${FASTRTPS_DEFAULT_PROFILES_FILE:-$PWD/config/fastdds_no_shm.xml}"
fi

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

COMPRESSED_ARG=()
if [ "${REALSENSE_COMPRESSED:-0}" = "1" ]; then
  COMPRESSED_ARG=(--compressed)
fi

exec /usr/bin/python3 scripts/realsense_mjpeg_bridge.py \
  --topic "${REALSENSE_COLOR_TOPIC:-/camera/camera/color/image_raw}" \
  "${COMPRESSED_ARG[@]}" \
  --host "${REALSENSE_STREAM_HOST:-127.0.0.1}" \
  --port "${REALSENSE_STREAM_PORT:-8080}" \
  --jpeg-quality "${REALSENSE_JPEG_QUALITY:-80}"
