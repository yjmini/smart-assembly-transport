#!/usr/bin/env bash
set -euo pipefail
CONVEYOR="ssafy@192.168.110.142"
TURTLEBOT="turtlebot4@192.168.110.174"

echo "== Conveyor Pi =="
ssh -o BatchMode=yes -o ConnectTimeout=5 "$CONVEYOR" 'hostname && python3 --version'

echo "== TurtleBot4 =="
ssh -o BatchMode=yes -o ConnectTimeout=5 "$TURTLEBOT" 'hostname && source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=34 && ros2 node list | head -20'
