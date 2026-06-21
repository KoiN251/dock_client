#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/.."

export ROS_DOMAIN_ID=42
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

DOCK_IP="${1:-100.87.209.105}"

zenoh-bridge-ros2dds -c config/zenoh/uav_ros2dds_bridge.json5 \
  -e "tcp/${DOCK_IP}:7447"
