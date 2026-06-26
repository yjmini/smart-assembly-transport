#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export REALSENSE_COLOR_TOPIC="${REALSENSE_COLOR_TOPIC:-/vision/yolo/annotated_image}"
# The detector publishes /vision/yolo/annotated_image with VOLATILE durability.
# The raw RealSense camera stream may need TRANSIENT_LOCAL, but the local YOLO
# annotated topic will not match a TRANSIENT_LOCAL subscriber.
export REALSENSE_DURABILITY="${REALSENSE_DURABILITY:-volatile}"
exec scripts/start_realsense_stream.sh
