#!/usr/bin/env bash
set -euo pipefail

ROBOT_HOST="${TURTLEBOT_HOST:-turtlebot4@192.168.110.174}"
ROBOT_IP="${ROBOT_HOST#*@}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-34}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/humble/setup.bash}"

printf '== Local/operator PC clock ==\n'
date +%s.%N
date -Ins

printf '\n== TurtleBot clock over SSH ==\n'
printf 'Robot host: %s\n' "$ROBOT_HOST"
if command -v ping >/dev/null 2>&1; then
  printf '\n-- ping %s --\n' "$ROBOT_IP"
  ping -c 1 -W 2 "$ROBOT_IP" || printf 'WARN: ping to %s failed. Robot may be on another Wi-Fi/VPN, powered off, or using a different IP.\n' "$ROBOT_IP" >&2
fi
if ssh -o BatchMode=yes -o ConnectTimeout=5 "$ROBOT_HOST" 'date +%s.%N && date -Ins'; then
  printf '\nClock check OK: compare the first local and robot epoch values. Difference should be < 0.1s for stable TF.\n'
else
  printf 'WARN: Could not SSH to %s. Check Wi-Fi/IP/SSH before diagnosing cross-machine TF.\n' "$ROBOT_HOST" >&2
fi

printf '\n== ROS TF quick probes ==\n'
set +u
if [ -f "$ROS_SETUP" ]; then
  # shellcheck disable=SC1090
  source "$ROS_SETUP"
fi
set -u
export ROS_DOMAIN_ID
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"

printf 'ROS_DOMAIN_ID=%s ROS_LOCALHOST_ONLY=%s\n' "$ROS_DOMAIN_ID" "$ROS_LOCALHOST_ONLY"
printf '\n-- visible ROS nodes --\n'
ros2 node list 2>/dev/null | sed -n '1,80p' || printf 'ros2 node list failed. Is ROS sourced and is the daemon healthy?\n'

printf '\n-- visible ROS topics likely needed by Nav2 --\n'
ros2 topic list 2>/dev/null | grep -E '^/(tf|tf_static|scan|odom|amcl_pose|map|global_costmap|local_costmap|navigate_to_pose|clock)$|^/.*costmap' | sed -n '1,120p' || true

printf '\n-- known TF frames from tf2_tools, if available --\n'
tmp_frames="/tmp/nav2_tf_frames_$$"
if timeout 6 ros2 run tf2_tools view_frames --ros-args -p quiet:=true >/tmp/view_frames.out 2>/tmp/view_frames.err; then
  grep -E 'map|odom|base_link|base_footprint|laser|scan' frames.yaml 2>/dev/null | sed -n '1,80p' || true
  rm -f frames.yaml frames.pdf
else
  sed -n '1,30p' /tmp/view_frames.err
fi
rm -f "$tmp_frames" /tmp/view_frames.out /tmp/view_frames.err

printf '\n-- /clock topic, if any --\n'
timeout 3 ros2 topic echo /clock --once 2>/dev/null || printf 'No /clock sample received; real hardware should normally use wall-clock time.\n'

printf '\n-- map -> base_link latest transform --\n'
timeout 5 ros2 run tf2_ros tf2_echo map base_link 2>/tmp/tf2_echo.err | sed -n '1,12p' || {
  printf 'tf2_echo failed; stderr:\n'
  sed -n '1,40p' /tmp/tf2_echo.err
}

printf '\n-- node use_sim_time parameters containing true --\n'
ros2 node list 2>/dev/null | while read -r node; do
  [ -z "$node" ] && continue
  value=$(ros2 param get "$node" use_sim_time 2>/dev/null | tr -d '\r' || true)
  case "$value" in
    *True*|*true*) printf '%s -> %s\n' "$node" "$value" ;;
  esac
done
