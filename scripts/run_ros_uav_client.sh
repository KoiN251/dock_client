#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/../uav_ws"

source /opt/ros/jazzy/setup.bash
source install/setup.bash

export ROS_DOMAIN_ID=42
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

UAV_ID="${1:-uav_01}"
DOCK_ID="${2:-dock_01}"

ros2 run uav_dock_client uav_dock_client_node \
  --ros-args \
  -p uav_id:=${UAV_ID} \
  -p dock_id:=${DOCK_ID}
