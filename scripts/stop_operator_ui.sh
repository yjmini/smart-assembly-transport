#!/usr/bin/env bash
set -euo pipefail

# Stop local operator-dashboard processes that commonly cause "address already in use".
# This intentionally does NOT stop remote TurtleBot/Conveyor or Dobot bringup.
patterns=(
  "python3 -m server.app"
  "manage.py runserver"
  "vite --host 0.0.0.0 --port 3000"
  "scripts/realsense_mjpeg_bridge.py"
  "realsense_object_detector"
  "scripts/turtlebot_pose_ws_bridge.py"
  "scripts/task_status_ws_bridge.py"
)

for pattern in "${patterns[@]}"; do
  pkill -f "$pattern" 2>/dev/null || true
done

sleep 0.5

for pattern in "${patterns[@]}"; do
  pkill -9 -f "$pattern" 2>/dev/null || true
done

# If a child process kept the ports, free the local dashboard ports too.
for port in 3000 8000 8765 8080; do
  pids=$(ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $0}' | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 0.2
    kill -9 $pids 2>/dev/null || true
  fi
done

echo "Stopped local operator UI/backend/stream processes if they were running."
