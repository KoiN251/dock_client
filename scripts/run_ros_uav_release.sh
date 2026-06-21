#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "$0")/../uav_ws"

source /opt/ros/jazzy/setup.bash
source install/setup.bash

export ROS_DOMAIN_ID=42
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

UAV_ID="${1:-uav_01}"

ros2 service call "/uav/${UAV_ID}/release_dock" std_srvs/srv/Trigger '{}'
