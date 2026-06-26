#!/usr/bin/env bash
set -euo pipefail

# Start local dashboard processes for hardware debugging.
# Run RealSense/Dobot/TurtleBot bringup separately, then use this for:
# - Django API / DB / Ollama chatbot endpoint
# - WebSocket mission server
# - Vue dashboard
# - YOLO annotated MJPEG bridge
# - TurtleBot pose -> WebSocket bridge

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/logs/operator-ui"
mkdir -p "$LOG_DIR"
cd "$ROOT"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-34}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"

start_bg() {
  local name="$1"; shift
  echo "Starting $name ... log: $LOG_DIR/$name.log"
  nohup "$@" >"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$LOG_DIR/$name.pid"
}

start_shell_bg() {
  local name="$1"; shift
  echo "Starting $name ... log: $LOG_DIR/$name.log"
  nohup bash -lc "$*" >"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$LOG_DIR/$name.pid"
}

start_shell_bg django "cd '$ROOT' && SMART_ASSEMBLY_DB_BACKEND=sqlite python3 manage.py runserver 0.0.0.0:8000"
start_shell_bg websocket "cd '$ROOT' && python3 -m server.app"
start_shell_bg vue "cd '$ROOT/web' && npm run dev"
start_shell_bg yolo_detector "cd '$ROOT' && scripts/start_yolo_detector.sh"
start_shell_bg yolo_stream "cd '$ROOT' && scripts/start_yolo_annotated_stream.sh"
start_shell_bg turtlebot_pose "cd '$ROOT' && scripts/start_turtlebot_pose_bridge.sh"
start_shell_bg task_status "cd '$ROOT' && source /opt/ros/humble/setup.bash && source sem1_pjt_ws/install/setup.bash && /usr/bin/python3 scripts/task_status_ws_bridge.py"

cat <<MSG

Started local operator UI stack.
Open: http://127.0.0.1:3000/#/progress
YOLO stream health: curl http://127.0.0.1:8080/health
Logs: $LOG_DIR

If a port was already in use, run:
  scripts/stop_operator_ui.sh
  scripts/start_operator_ui.sh
MSG
