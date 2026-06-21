# CTUAV UAV Dock Client

Tài liệu kiến trúc, pipeline, giải thích Python/ROS 2 và hướng dẫn maintain:
[docs/README.md](docs/README.md).

Source này chạy trên UAV companion/laptop.

Nhiệm vụ:

- Tự động request Dock.
- Dùng `DockState` làm nguồn xác nhận session.
- Nhận Dock GPS/Beacon và contact qua Zenoh.
- Gửi UAV GPS và status heartbeat về Dock.
- Chuyển sang `CONTACTED` khi cảm biến Dock xác nhận chạm landing pad.
- Gửi release và ngăn tự reserve lại sau khi release thành công.

GPS UAV hiện là dữ liệu giả. Điều khiển approach, PX4 và precision landing chưa
thuộc node MVP này.
