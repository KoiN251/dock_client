#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

DOCK_IP="${1:-100.87.209.105}"

source ~/zenoh_venv/bin/activate

python3 tools/zenoh_uav/uav_node.py \
  --config config/uav.yaml \
  --connect tcp/${DOCK_IP}:7447
