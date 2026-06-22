# CTUAV Dock–UAV MVP Test Guide

> `DockGps` v2 thay đổi type hash. Sau khi pull phải xóa `build/install/log` và
> build lại cả workspace Dock lẫn UAV trước khi chạy Zenoh bridge.

Hướng dẫn end-to-end chính được lưu cùng source Dock để tránh hai bản tài liệu
bị lệch nhau:

- Local nếu hai repo nằm chung thư mục: `../../mobile_dock/docs/TEST_GUIDE.md`
- GitHub: https://github.com/KoiN251/mobile_dock/blob/feature/dock-uav-mvp-test/docs/TEST_GUIDE.md

Các lệnh nhanh phía UAV:

```bash
cd ~/dock_client/uav_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
cd ..

# Terminal 1
./scripts/run_bridge_uav.sh <DOCK_NETBIRD_IP>

# Terminal 2
./scripts/run_ros_uav_client.sh uav_01 dock_01

# Terminal 3: bắt đầu request
./scripts/run_ros_uav_request.sh uav_01

# Sau contact=false: release
./scripts/run_ros_uav_release.sh uav_01
```

Kiểm tra dữ liệu Dock GPS/Beacon mà UAV nhận được:

```bash
ros2 topic hz /dock/dock_01/beacon
ros2 topic echo --once /dock/dock_01/beacon
```
