# CTUAV UAV Dock Client: Architecture and Maintenance Guide

Tài liệu này dành cho người chạy laptop/companion computer như một UAV client.
Nó cũng mô tả contract với source `mobile_dock` để có thể debug end-to-end.

```text
Dock: mobile_dock trên Raspberry Pi 5
UAV:  ctuav_uav_dock_client trên laptop/companion
```

## 1. Pipeline end-to-end

```text
DOCK
GPSD input + filter node → DockGps → DockBeacon ┐
                                               │
state manager → DockState ─────────────────────┤
contact sensor → DockContact ──────────────────┤
                                               │ Zenoh/NetBird
═══════════════════════════════════════════════╪════════════
                                               │
UAV                                            ▼
                                     uav_dock_client_node
                                               │
                    ┌──────────────────────────┴──────────┐
                    ▼                                     ▼
             UavStatus 1 Hz                         UavGps 1 Hz
                                                       (accepted only)
```

Luồng session:

```text
IDLE
  → flight logic/operator gọi /uav/uav_01/request_dock
  → bật request_enabled, UAV chờ/gửi/retry ReserveDock
  → REQUESTING_DOCK
  → DockState RESERVED cho uav_01
  → APPROACHING_DOCK
  → trao đổi GPS/status
  → DockContact true
  → CONTACTED
  → contact false + ReleaseDock
  → IDLE, request_enabled=false
```

`CONTACTED` chỉ có nghĩa UAV chạm landing pad. Nó không thay thế xác nhận
`LANDED` hoặc `DISARMED` từ PX4.

## 2. Cấu trúc source

```text
uav_ws/src/
├── dock_interfaces/
│   ├── msg/
│   │   ├── DockGps.msg
│   │   ├── DockState.msg
│   │   ├── DockBeacon.msg
│   │   ├── DockContact.msg
│   │   ├── UavGps.msg
│   │   └── UavStatus.msg
│   └── srv/
│       ├── ReserveDock.srv
│       └── ReleaseDock.srv
└── uav_dock_client/
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    └── uav_dock_client/
        └── uav_dock_client_node.py
```

Không sửa file trong `build/`, `install/` hoặc `log/`.

## 3. ROS 2 và Python cơ bản

Node là một chương trình ROS nhỏ. Topic truyền dữ liệu liên tục; service dùng
cho request/response. Callback là hàm ROS tự gọi khi có message, timer hoặc
service event.

```python
class UavDockClientNode(Node):
    def __init__(self):
        super().__init__('uav_dock_client_node')
```

`self` là node hiện tại. `__init__` chạy một lần khi node khởi động.

```python
self.status_pub = self.create_publisher(
    UavStatus,
    f'/uav/{self.uav_id}/status',
    10,
)
```

Đoạn trên tạo publisher. `f'...'` là Python f-string, dùng để chèn giá trị biến
vào chuỗi. Số `10` là queue depth của QoS.

```python
self.dock_state_sub = self.create_subscription(
    DockState,
    self.state_topic,
    self.on_dock_state,
    10,
)
```

Mỗi message mới sẽ gọi `on_dock_state(msg)`.

Service local `/uav/<uav_id>/request_dock` dùng `std_srvs/srv/Trigger`. Callback
bật flag `request_enabled`. Timer chỉ chạy logic chờ/gửi/retry khi flag này bật.

Python không yêu cầu `else: return` ở cuối một `if`; khi tới cuối hàm, hàm tự
kết thúc. Early return nên dùng để loại input không hợp lệ trước.

## 4. Interface với Dock

### DockState

```text
IDLE=0
RESERVED=1
CONTACTED=2
FAULT=255
```

UAV phải kiểm tra đồng thời `dock_id`, state và `reserved_uav_id`.

### DockBeacon

```text
DockBeacon
├── DockGps gps
└── DockState state
```

GPS và state giữ timestamp độc lập:

```text
beacon.gps.stamp_unix
beacon.state.stamp_unix
```

Việc đóng gói không ghi đè timestamp hay `dock_id`. Beacon là snapshot của GPS
mới nhất và state mới nhất, vì vậy hai timestamp có thể lệch nhẹ.

### DockContact

Dock phát contact sensor state 10 Hz. UAV chỉ dùng message khi `valid=true` và
đúng `uav_id`.

### UavStatus

UAV phát 1 Hz kể cả trước khi accepted. Message mô tả state, battery, GPS health
và `accepted_by_dock`.

### UavGps

UAV chỉ phát 1 Hz sau khi accepted. Hiện dữ liệu lấy từ ROS parameter giả. Khi
tích hợp PX4, giữ nguyên output `/uav/<uav_id>/gps` và thay nguồn dữ liệu.

### ReserveDock và ReleaseDock

Reserve là trigger. `DockState` là source-of-truth vì được publish liên tục và
vẫn xác nhận session nếu service response bị chậm qua bridge.

Dock từ chối release nếu contact sensor vẫn active. Reset contact trước khi
release.

## 5. uav_dock_client_node.py

### Parameters

```text
uav_id, dock_id
heartbeat_hz, gps_hz
battery_percent
fake latitude/longitude/altitude
fake NED velocity và heading
```

Parameter có thể đổi bằng `--ros-args -p name:=value` mà không sửa source.

### Runtime state

```text
accepted             Dock đã dành cho UAV.
request_enabled      User/flight logic đã cho phép tìm và reserve Dock.
request_in_flight    Đang chờ service response.
last_request_time    Dùng để retry request bị treo sau 3 giây.
uav_state            State hiện tại của UAV client.
seq/gps_seq          Sequence độc lập cho status và GPS.
```

### Request theo command

Client không request khi vừa start. Flight logic hoặc operator gọi service local
`/uav/<uav_id>/request_dock` để bật flag. Client thử ngay, sau đó timer mỗi giây
tiếp tục chờ service và retry request bị treo quá 3 giây. Response bị reject cũng
được thử lại khi timer chạy tiếp. Gọi release sẽ tắt flag.

### Xác nhận accepted

Có hai đường:

1. `ReserveDock` response trả `accepted=true`.
2. `DockState` báo `RESERVED`/`CONTACTED` cho đúng UAV.

Đường thứ hai là nguồn sự thật chính.

### Kích hoạt session

Client đặt `accepted=true`, chuyển sang `APPROACHING_DOCK`, rồi tạo subscriber
cho Beacon và Contact đúng một lần.

### Nhận Beacon

Hiện callback chỉ log GPS/state. Đây là điểm nối sang navigation/PX4:

```text
Dock GPS → approach waypoint → PX4 goto → precision landing
```

Nên tách điều khiển bay sang package riêng thay vì làm `uav_dock_client_node`
ngày càng lớn.

### Nhận contact

Khi `contact=true`, đúng UAV và message valid, client chuyển sang
`UavStatus.CONTACTED`. Không dùng contact đơn lẻ để khẳng định landed/disarmed.

### Request và release

Hai script gọi hai service cục bộ. Request bật state machine; release tắt nó
trước khi gửi remote `ReleaseDock`. Sau này flight logic có thể gọi chính các
service này khi nhận flag request/release:

```text
/uav/<uav_id>/request_dock
/uav/<uav_id>/release_dock
```

## 6. Zenoh

ROS 2 DDS discovery được giới hạn trong từng máy. `zenoh-bridge-ros2dds` chuyển
ROS graph qua NetBird:

```text
UAV ROS nodes ↔ UAV bridge ↔ TCP/NetBird ↔ Dock bridge ↔ Dock ROS nodes
```

IP Dock chỉ được truyền cho `run_bridge_uav.sh`:

```bash
./scripts/run_bridge_uav.sh <DOCK_NETBIRD_IP>
```

Node Python không phụ thuộc IP.

## 7. Build và chạy

```bash
cd ~/CTUAV/ctuav_uav_dock_client/uav_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Terminal bridge:

```bash
cd ~/CTUAV/ctuav_uav_dock_client
./scripts/run_bridge_uav.sh <DOCK_NETBIRD_IP>
```

Terminal client:

```bash
./scripts/run_ros_uav_client.sh uav_01 dock_01
```

Phát một request Dock:

```bash
./scripts/run_ros_uav_request.sh uav_01
```

Release sau khi Dock contact đã reset false:

```bash
./scripts/run_ros_uav_release.sh uav_01
```

## 8. Debug

```bash
ros2 topic echo /dock/dock_01/state
ros2 topic echo /dock/dock_01/beacon
ros2 topic echo /dock/dock_01/contact
ros2 topic echo /uav/uav_01/gps
ros2 topic echo /uav/uav_01/status
ros2 service list | grep dock
```

Mạng:

```bash
ping <DOCK_NETBIRD_IP>
nc -vz <DOCK_NETBIRD_IP> 7447
```

## 9. Hướng phát triển

1. Tách fake UAV GPS thành package `uav_gps_drivers`.
2. Subscribe PX4 vehicle global position và chuyển sang `UavGps`.
3. Tạo node approach riêng nhận DockBeacon và điều khiển PX4.
4. Nối `CONTACTED` với terminator như một tín hiệu pad contact.
5. Dùng PX4 land detector để tạo `LANDED` thật.
6. Dùng armed state để tạo `DISARMED` thật.
7. Thêm watchdog/fault khi mất DockState hoặc Beacon.

## 10. Quy trình maintain

- Chỉ sửa `src/`, `scripts/`, `config/`, `docs/`.
- Chạy `python3 -m compileall -q src` sau khi sửa Python.
- Rebuild khi sửa dependency, setup, message hoặc service.
- Interface ở Dock và UAV phải giống nhau.
- Không chạy lại `setup_ros_uav_minimal.sh` trong deploy thông thường vì đây là
  bootstrap script cũ có thể ghi đè source.
- Không kích hoạt hành động safety-critical chỉ từ contact sensor.
