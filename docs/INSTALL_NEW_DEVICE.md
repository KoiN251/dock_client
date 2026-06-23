# Cài UAV Dock Client lên thiết bị mới

Tài liệu này dành cho máy đóng vai UAV companion/laptop. Hướng dẫn Dock đầy đủ
nằm trong source `mobile_dock/docs/INSTALL_NEW_DEVICE.md`.

## 1. Máy UAV cần gì?

- Ubuntu 24.04.
- ROS 2 Jazzy.
- NetBird để kết nối tới Dock.
- `zenoh-bridge-ros2dds`.
- Repo `KoiN251/dock_client`.

MVP hiện tại chưa điều khiển PX4. UAV GPS/status đang là heartbeat giả để test
communication với Dock.

## 2. Cài tool nền

```bash
sudo apt update
sudo apt install -y git curl gnupg ca-certificates lsb-release \
  python3-pip python3-yaml python3-colcon-common-extensions \
  netcat-openbsd jq
```

Nếu chưa cài ROS 2 Jazzy, cài theo hướng dẫn chính thức cho Ubuntu 24.04. Sau đó
kiểm tra:

```bash
source /opt/ros/jazzy/setup.bash
ros2 --help
```

## 3. Cài NetBird

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sh
netbird up
netbird status
```

Nếu dùng setup key:

```bash
netbird up --setup-key <SETUP_KEY>
netbird status
```

UAV cần biết NetBird IP của Dock, ví dụ:

```text
DOCK_NETBIRD_IP=100.87.209.105
```

## 4. Cài Zenoh bridge

MVP này dùng `zenoh-bridge-ros2dds` standalone. Không cần chạy `zenohd`.

```bash
sudo mkdir -p /etc/apt/keyrings
curl -L https://download.eclipse.org/zenoh/debian-repo/zenoh-public-key \
  | sudo gpg --dearmor --yes --output /etc/apt/keyrings/zenoh-public-key.gpg
echo "deb [signed-by=/etc/apt/keyrings/zenoh-public-key.gpg] https://download.eclipse.org/zenoh/debian-repo/ /" \
  | sudo tee /etc/apt/sources.list.d/zenoh.list
sudo apt update
sudo apt install -y zenoh-bridge-ros2dds
```

Kiểm tra:

```bash
command -v zenoh-bridge-ros2dds
zenoh-bridge-ros2dds -h
```

## 5. Clone source

```bash
mkdir -p ~/CTUAV
cd ~/CTUAV
git clone git@github.com:KoiN251/dock_client.git dock_client
cd dock_client
git switch main
```

Nếu SSH lỗi, kiểm tra:

```bash
ssh -T git@github.com
```

## 6. Build

```bash
cd ~/CTUAV/dock_client/uav_ws
source /opt/ros/jazzy/setup.bash
rm -rf build install log
colcon build --symlink-install
source install/setup.bash
```

Kiểm tra:

```bash
ros2 pkg prefix dock_interfaces
ros2 pkg prefix uav_dock_client
```

## 7. Chạy từng terminal phía UAV

### Terminal 1 — Zenoh bridge

```bash
cd ~/CTUAV/dock_client
./scripts/run_bridge_uav.sh <DOCK_NETBIRD_IP>
```

Ví dụ:

```bash
./scripts/run_bridge_uav.sh 100.87.209.105
```

### Terminal 2 — UAV client

```bash
cd ~/CTUAV/dock_client
./scripts/run_ros_uav_client.sh uav_01 dock_01
```

Khi vừa start, node không tự request Dock.

### Terminal 3 — request/release

Bật request:

```bash
cd ~/CTUAV/dock_client
./scripts/run_ros_uav_request.sh uav_01
```

Release:

```bash
./scripts/run_ros_uav_release.sh uav_01
```

## 8. Kiểm tra UAV đã nhận Dock chưa

```bash
ros2 topic list | grep dock
ros2 service list | grep dock
ros2 topic hz /dock/dock_01/beacon
ros2 topic echo --once /dock/dock_01/beacon
ros2 topic echo --once /dock/dock_01/state
```

Kiểm tra port Zenoh tới Dock:

```bash
nc -vz <DOCK_NETBIRD_IP> 7447
```

## 9. Lỗi thường gặp

### `Package not found`

Chưa build hoặc chưa source:

```bash
cd ~/CTUAV/dock_client/uav_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Nếu vẫn lỗi:

```bash
rm -rf build install log
colcon build --symlink-install
```

### Không thấy Dock beacon

Kiểm tra:

1. Dock bridge đã chạy chưa.
2. UAV bridge có connect đúng `<DOCK_NETBIRD_IP>` chưa.
3. Dock đã được reserve chưa. Beacon chỉ publish sau khi Dock `RESERVED`.
4. `nc -vz <DOCK_NETBIRD_IP> 7447` có thành công không.
5. Cả hai bên đang dùng `ROS_DOMAIN_ID=42`.

### Có cần cài `zenohd` không?

Không. Client hiện tại chỉ cần `zenoh-bridge-ros2dds`.
