#!/usr/bin/env bash
set -e

sudo apt update
sudo apt install -y python3-pip python3-venv python3-yaml

python3 -m venv ~/zenoh_venv
source ~/zenoh_venv/bin/activate

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install eclipse-zenoh pyyaml

echo "[OK] UAV Zenoh environment ready"
