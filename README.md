# CTUAV UAV Dock Client

Tài liệu kiến trúc, pipeline, giải thích Python/ROS 2 và hướng dẫn maintain:
[docs/README.md](docs/README.md).

Thứ tự đọc khuyến nghị:

1. Đọc pipeline và state trong [docs/README.md](docs/README.md).
2. Mở `uav_dock_client_node.py` và theo callback map trong tài liệu.
3. Dùng [docs/TEST_GUIDE.md](docs/TEST_GUIDE.md) để quan sát cùng dữ liệu trên
   topic trước khi sửa logic.

Lưu đồ Mermaid của client:
[flow đầy đủ](docs/UAV_CLIENT_FLOW.mmd) và
[state machine](docs/UAV_CLIENT_STATE.mmd).

Hướng dẫn test end-to-end: [docs/TEST_GUIDE.md](docs/TEST_GUIDE.md).

Hướng dẫn cài lên thiết bị mới:
[docs/INSTALL_NEW_DEVICE.md](docs/INSTALL_NEW_DEVICE.md).

Source này chạy trên UAV companion/laptop.

Nhiệm vụ:

- Lệnh local `/uav/<uav_id>/request_dock` bật chu trình chờ/retry Dock.
- Dùng `DockState` làm nguồn xác nhận session.
- Nhận Dock GPS/Beacon và contact qua Zenoh.
- Gửi UAV GPS và status heartbeat về Dock.
- Chuyển sang `CONTACTED` khi cảm biến Dock xác nhận chạm landing pad.
- Lệnh release tắt chu trình request rồi gửi release sang Dock.

GPS UAV hiện là dữ liệu giả. Điều khiển approach, PX4 và precision landing chưa
thuộc node MVP này.
