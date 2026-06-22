# CTUAV UAV Dock Client

Tài liệu kiến trúc, pipeline, giải thích Python/ROS 2 và hướng dẫn maintain:
[docs/README.md](docs/README.md).

Hướng dẫn test end-to-end: [docs/TEST_GUIDE.md](docs/TEST_GUIDE.md).

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
