#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export REALSENSE_COLOR_TOPIC="${REALSENSE_COLOR_TOPIC:-/vision/yolo/annotated_image}"
exec scripts/start_realsense_stream.sh
