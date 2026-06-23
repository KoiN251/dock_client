#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[SETUP] CTUAV UAV ROS minimal client"

mkdir -p uav_ws/src

# ============================================================
# 1. dock_interfaces copy
# ============================================================

mkdir -p uav_ws/src/dock_interfaces/msg
mkdir -p uav_ws/src/dock_interfaces/srv

cat > uav_ws/src/dock_interfaces/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>dock_interfaces</name>
  <version>0.0.1</version>
  <description>CTUAV Dock ROS 2 interfaces.</description>
  <maintainer email="ctuav@example.com">ctuav</maintainer>
  <license>BSD-3-Clause</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <build_depend>rosidl_default_generators</build_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>

  <member_of_group>rosidl_interface_packages</member_of_group>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
EOF

cat > uav_ws/src/dock_interfaces/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(dock_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DockGps.msg"
  "msg/DockState.msg"
  "msg/DockBeacon.msg"
  "msg/DockContact.msg"
  "msg/UavStatus.msg"
  "msg/UavGps.msg"
  "srv/ReserveDock.srv"
  "srv/ReleaseDock.srv"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
EOF

# Message files must match Dock source exactly.
cat > uav_ws/src/dock_interfaces/msg/DockGps.msg <<'EOF'
uint8 interface_version
string dock_id
uint32 seq
float64 stamp_unix

float64 latitude_deg
float64 longitude_deg
float64 altitude_m

float32 vel_n_m_s
float32 vel_e_m_s
float32 vel_d_m_s

float32 heading_deg
bool heading_valid

uint8 fix_type
uint8 satellites_used
float32 eph_m
float32 epv_m
float32 s_variance_m_s

bool gps_ok
bool velocity_valid

string source_type
EOF

cat > uav_ws/src/dock_interfaces/msg/DockState.msg <<'EOF'
uint8 interface_version
string dock_id
uint32 seq
float64 stamp_unix

uint8 IDLE=0
uint8 RESERVED=1
uint8 CONTACTED=2
uint8 FAULT=255

uint8 state
bool available
string reserved_uav_id

bool gps_ok
bool hardware_ok
string reason
EOF

cat > uav_ws/src/dock_interfaces/msg/DockBeacon.msg <<'EOF'
DockGps gps
DockState state
EOF

cat > uav_ws/src/dock_interfaces/msg/DockContact.msg <<'EOF'
uint8 interface_version
string dock_id
string uav_id
uint32 seq
float64 stamp_unix

bool contact
bool valid
string sensor_id
EOF

cat > uav_ws/src/dock_interfaces/msg/UavStatus.msg <<'EOF'
uint8 interface_version
string uav_id
string dock_id
uint32 seq
float64 stamp_unix

uint8 IDLE=0
uint8 APPROACHING_DOCK=1
uint8 LANDED=2
uint8 ABORTING=3
uint8 FAULT=255

uint8 uav_state

float32 battery_percent
bool gps_ok
bool accepted_by_dock
EOF

cat > uav_ws/src/dock_interfaces/msg/UavGps.msg <<'EOF'
# UAV GPS heartbeat sent to its dedicated Dock.
# altitude_m is AMSL.

uint8 interface_version
string uav_id
uint32 seq
float64 stamp_unix

float64 latitude_deg
float64 longitude_deg
float64 altitude_m

float32 heading_deg

float32 eph_m
float32 epv_m
bool gps_ok
EOF

cat > uav_ws/src/dock_interfaces/srv/ReserveDock.srv <<'EOF'
string dock_id
string uav_id
bool request_gps
---
bool accepted
string reason
string gps_topic
string contact_topic
EOF

cat > uav_ws/src/dock_interfaces/srv/ReleaseDock.srv <<'EOF'
string dock_id
string uav_id
---
bool accepted
string reason
EOF

# ============================================================
# 2. uav_dock_client
# ============================================================

mkdir -p uav_ws/src/uav_dock_client/uav_dock_client
mkdir -p uav_ws/src/uav_dock_client/resource

touch uav_ws/src/uav_dock_client/resource/uav_dock_client
touch uav_ws/src/uav_dock_client/uav_dock_client/__init__.py

cat > uav_ws/src/uav_dock_client/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>uav_dock_client</name>
  <version>0.0.1</version>
  <description>CTUAV UAV Dock client.</description>
  <maintainer email="ctuav@example.com">ctuav</maintainer>
  <license>BSD-3-Clause</license>

  <buildtool_depend>ament_python</buildtool_depend>

  <depend>rclpy</depend>
  <depend>dock_interfaces</depend>
  <depend>px4_msgs</depend>
  <depend>std_srvs</depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
EOF

cat > uav_ws/src/uav_dock_client/setup.cfg <<'EOF'
[develop]
script_dir=$base/lib/uav_dock_client
[install]
install_scripts=$base/lib/uav_dock_client
EOF

cat > uav_ws/src/uav_dock_client/setup.py <<'EOF'
from setuptools import setup

package_name = 'uav_dock_client'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ctuav',
    maintainer_email='ctuav@example.com',
    description='CTUAV UAV Dock client.',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'uav_dock_client_node = uav_dock_client.uav_dock_client_node:main',
        ],
    },
)
EOF

cat > uav_ws/src/uav_dock_client/uav_dock_client/uav_dock_client_node.py <<'EOF'
#!/usr/bin/env python3
"""
uav_dock_client_node

INPUT:
  - ReserveDock response
  - DockBeacon
  - DockContact

OUTPUT:
  - ReserveDock request
  - UavStatus heartbeat

Sau này:
  - DockBeacon output có thể đưa vào preland/precision landing.
  - DockContact có thể đưa vào state machine UAV.
"""

import time
import rclpy
from rclpy.node import Node

from dock_interfaces.msg import DockBeacon, DockContact, UavStatus
from dock_interfaces.srv import ReserveDock


class UavDockClientNode(Node):
    def __init__(self):
        super().__init__('uav_dock_client_node')

        self.declare_parameter('uav_id', 'uav_01')
        self.declare_parameter('dock_id', 'dock_01')
        self.declare_parameter('heartbeat_hz', 1.0)
        self.declare_parameter('battery_percent', 80.0)

        self.uav_id = self.get_parameter('uav_id').value
        self.dock_id = self.get_parameter('dock_id').value
        self.heartbeat_hz = float(self.get_parameter('heartbeat_hz').value)
        self.battery_percent = float(self.get_parameter('battery_percent').value)

        self.accepted = False
        self.request_in_flight = False
        self.uav_state = UavStatus.IDLE
        self.seq = 0

        self.reserve_client = self.create_client(
            ReserveDock,
            f'/dock/{self.dock_id}/reserve',
        )

        self.status_pub = self.create_publisher(
            UavStatus,
            f'/uav/{self.uav_id}/status',
            10,
        )

        self.beacon_sub = None
        self.contact_sub = None

        self.request_timer = self.create_timer(1.0, self.request_dock_if_needed)
        self.heartbeat_timer = self.create_timer(1.0 / self.heartbeat_hz, self.publish_status)

        self.get_logger().info(f'UAV Dock Client started uav_id={self.uav_id}, dock_id={self.dock_id}')

    def request_dock_if_needed(self):
        if self.accepted or self.request_in_flight:
            return

        if not self.reserve_client.wait_for_service(timeout_sec=0.1):
            self.get_logger().warn('Waiting for reserve service...')
            return

        req = ReserveDock.Request()
        req.dock_id = self.dock_id
        req.uav_id = self.uav_id
        req.request_gps = True

        self.request_in_flight = True
        self.get_logger().info('Sending reserve request...')

        future = self.reserve_client.call_async(req)
        future.add_done_callback(self.on_reserve_response)

    def on_reserve_response(self, future):
        self.request_in_flight = False

        try:
            resp = future.result()
        except Exception as e:
            self.get_logger().error(f'Reserve request failed: {e}')
            return

        self.get_logger().info(f'Reserve response accepted={resp.accepted}, reason={resp.reason}')

        if not resp.accepted:
            return

        self.accepted = True
        self.uav_state = UavStatus.APPROACHING_DOCK

        self.beacon_sub = self.create_subscription(
            DockBeacon,
            resp.gps_topic,
            self.on_beacon,
            10,
        )

        self.contact_sub = self.create_subscription(
            DockContact,
            resp.contact_topic,
            self.on_contact,
            10,
        )

        self.get_logger().info(f'Subscribed beacon : {resp.gps_topic}')
        self.get_logger().info(f'Subscribed contact: {resp.contact_topic}')

    def on_beacon(self, msg: DockBeacon):
        gps = msg.gps
        state = msg.state

        self.get_logger().info(
            f'DockBeacon gps_seq={gps.seq} '
            f'lat={gps.latitude_deg:.7f} lon={gps.longitude_deg:.7f} '
            f'alt={gps.altitude_m:.2f} '
            f'velN={gps.vel_n_m_s:.2f} velE={gps.vel_e_m_s:.2f} velD={gps.vel_d_m_s:.2f} '
            f'eph={gps.eph_m:.2f} epv={gps.epv_m:.2f} '
            f'dock_state={state.state}'
        )

    def on_contact(self, msg: DockContact):
        if not msg.valid:
            return

        self.get_logger().info(f'DockContact contact={msg.contact}, sensor={msg.sensor_id}')

        if msg.contact and msg.uav_id == self.uav_id:
            self.uav_state = UavStatus.CONTACTED
            self.get_logger().info('UAV state -> CONTACTED')

    def publish_status(self):
        msg = UavStatus()
        msg.interface_version = 1
        msg.uav_id = self.uav_id
        msg.dock_id = self.dock_id
        msg.seq = self.seq
        msg.stamp_unix = time.time()
        msg.uav_state = self.uav_state
        msg.battery_percent = float(self.battery_percent)
        msg.gps_ok = True
        msg.accepted_by_dock = self.accepted

        self.status_pub.publish(msg)

        self.get_logger().info(
            f'UavStatus seq={self.seq} state={msg.uav_state} accepted={msg.accepted_by_dock}'
        )

        self.seq += 1


def main(args=None):
    rclpy.init(args=args)
    node = UavDockClientNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
EOF

# ============================================================
# 3. Run helper
# ============================================================

cat > scripts/run_ros_uav_client.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../uav_ws"

source /opt/ros/jazzy/setup.bash
source install/setup.bash

UAV_ID="${1:-uav_01}"
DOCK_ID="${2:-dock_01}"

ros2 run uav_dock_client uav_dock_client_node \
  --ros-args \
  -p uav_id:=${UAV_ID} \
  -p dock_id:=${DOCK_ID}
EOF

chmod +x scripts/run_ros_uav_client.sh

echo "[OK] UAV ROS minimal setup generated."
echo ""
echo "Build:"
echo "  cd uav_ws"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  colcon build"
echo "  source install/setup.bash"
