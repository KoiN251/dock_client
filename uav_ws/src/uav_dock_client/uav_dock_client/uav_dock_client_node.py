#!/usr/bin/env python3
"""
uav_dock_client_node

Vai trò:
  - Publish UAV heartbeat/status
  - Nhận command local để bật/tắt chu trình request Dock
  - Subscribe DockState từ đầu
  - Nếu DockState báo reserved_uav_id == uav_id thì tự accepted=True
  - Sau khi accepted thì subscribe DockBeacon và DockContact

Lý do thiết kế:
  - Service response qua bridge có thể bị treo/chậm.
  - DockState topic là source-of-truth vì publish liên tục.
"""

import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from dock_interfaces.msg import DockBeacon, DockContact, DockState, UavGps, UavStatus
from dock_interfaces.srv import ReleaseDock, ReserveDock
from px4_msgs.msg import BatteryStatus, VehicleGlobalPosition, VehicleLocalPosition
from std_srvs.srv import Trigger


def get_message_name_version(msg_class):
    """Return PX4 DDS topic suffix for versioned message definitions."""
    if msg_class.MESSAGE_VERSION == 0:
        return ''
    return f'_v{msg_class.MESSAGE_VERSION}'


def px4_out_topic(topic_name: str, msg_class) -> str:
    return f'/fmu/out/{topic_name}{get_message_name_version(msg_class)}'


class UavDockClientNode(Node):
    def __init__(self):
        super().__init__('uav_dock_client_node')

        # =========================
        # Parameters
        # =========================
        self.declare_parameter('uav_id', 'uav_01')
        self.declare_parameter('dock_id', 'dock_01')
        self.declare_parameter('heartbeat_hz', 1.0)
        self.declare_parameter('battery_percent', 80.0)
        self.declare_parameter('gps_hz', 1.0)
        self.declare_parameter('heartbeat_log_period_s', 10.0)
        self.declare_parameter('latitude_deg', 10.7755000)
        self.declare_parameter('longitude_deg', 106.6995000)
        self.declare_parameter('altitude_m', 30.0)
        self.declare_parameter('heading_deg', 0.0)
        self.declare_parameter('px4_data_timeout_s', 5.0)
        self.declare_parameter(
            'px4_battery_topic',
            px4_out_topic('battery_status', BatteryStatus),
        )
        self.declare_parameter(
            'px4_global_position_topic',
            px4_out_topic('vehicle_global_position', VehicleGlobalPosition),
        )
        self.declare_parameter(
            'px4_local_position_topic',
            px4_out_topic('vehicle_local_position', VehicleLocalPosition),
        )

        self.uav_id = self.get_parameter('uav_id').value
        self.dock_id = self.get_parameter('dock_id').value
        self.heartbeat_hz = float(self.get_parameter('heartbeat_hz').value)
        self.battery_percent = float(self.get_parameter('battery_percent').value)
        self.gps_hz = float(self.get_parameter('gps_hz').value)
        self.px4_data_timeout_s = float(
            self.get_parameter('px4_data_timeout_s').value
        )
        self.heartbeat_log_period_s = float(
            self.get_parameter('heartbeat_log_period_s').value
        )

        # =========================
        # Runtime state
        # =========================
        self.accepted = False
        self.request_enabled = False
        self.request_in_flight = False
        self.last_request_time = 0.0
        self.last_beacon_log_monotonic = None
        self.last_contact_state = None
        self.latest_px4_battery_percent = None
        self.latest_px4_global_position = None
        self.latest_px4_local_position = None
        self.last_px4_battery_monotonic = None
        self.last_px4_global_position_monotonic = None
        self.last_px4_local_position_monotonic = None

        self.uav_state = UavStatus.IDLE
        self.seq = 0
        self.gps_seq = 0

        # Topic mặc định. Nếu service response trả topic khác thì sẽ update lại.
        self.state_topic = f'/dock/{self.dock_id}/state'
        self.beacon_topic = f'/dock/{self.dock_id}/beacon'
        self.contact_topic = f'/dock/{self.dock_id}/contact'

        self.beacon_sub = None
        self.contact_sub = None

        # =========================
        # ROS entities
        # =========================
        self.reserve_client = self.create_client(
            ReserveDock,
            f'/dock/{self.dock_id}/reserve',
        )
        self.release_client = self.create_client(
            ReleaseDock,
            f'/dock/{self.dock_id}/release',
        )
        self.request_command_srv = self.create_service(
            Trigger,
            f'/uav/{self.uav_id}/request_dock',
            self.on_request_command,
        )
        self.release_command_srv = self.create_service(
            Trigger,
            f'/uav/{self.uav_id}/release_dock',
            self.on_release_command,
        )

        self.status_pub = self.create_publisher(
            UavStatus,
            f'/uav/{self.uav_id}/status',
            10,
        )
        self.gps_pub = self.create_publisher(
            UavGps,
            f'/uav/{self.uav_id}/gps',
            10,
        )

        # Subscribe DockState từ đầu.
        # Đây là source-of-truth để biết Dock đã reserve cho UAV chưa.
        self.dock_state_sub = self.create_subscription(
            DockState,
            self.state_topic,
            self.on_dock_state,
            10,
        )

        self.px4_battery_sub = self.create_subscription(
            BatteryStatus,
            self.get_parameter('px4_battery_topic').value,
            self.on_px4_battery,
            qos_profile_sensor_data,
        )
        self.px4_global_position_sub = self.create_subscription(
            VehicleGlobalPosition,
            self.get_parameter('px4_global_position_topic').value,
            self.on_px4_global_position,
            qos_profile_sensor_data,
        )
        self.px4_local_position_sub = self.create_subscription(
            VehicleLocalPosition,
            self.get_parameter('px4_local_position_topic').value,
            self.on_px4_local_position,
            qos_profile_sensor_data,
        )
        # Timers
        self.request_timer = self.create_timer(1.0, self.request_dock_if_needed)
        self.heartbeat_timer = self.create_timer(
            1.0 / self.heartbeat_hz,
            self.publish_status, # Publish heartbeat/status của UAV
        )
        self.gps_timer = self.create_timer(1.0 / self.gps_hz, self.publish_gps)

        self.get_logger().info('UavDockClientNode started')
        self.get_logger().info(f'  uav_id={self.uav_id}')
        self.get_logger().info(f'  dock_id={self.dock_id}')
        self.get_logger().info(f'  state_topic={self.state_topic}')
        self.get_logger().info(f'  reserve_service=/dock/{self.dock_id}/reserve')
        self.get_logger().info(
            f'  request_command=/uav/{self.uav_id}/request_dock'
        )
        self.get_logger().info(
            f'  px4_battery_topic={self.get_parameter("px4_battery_topic").value}'
        )
        self.get_logger().info(
            '  px4_global_position_topic='
            f'{self.get_parameter("px4_global_position_topic").value}'
        )
        self.get_logger().info(
            '  px4_local_position_topic='
            f'{self.get_parameter("px4_local_position_topic").value}'
        )
        self.get_logger().info(f'  px4_data_timeout_s={self.px4_data_timeout_s}')

    def is_px4_fresh(self, last_monotonic):
        if last_monotonic is None:
            return False
        return time.monotonic() - last_monotonic <= self.px4_data_timeout_s

    def on_px4_battery(self, msg: BatteryStatus):
        """Translate PX4 BatteryStatus.remaining [0..1] into UAV percent."""
        self.last_px4_battery_monotonic = time.monotonic()
        remaining = float(msg.remaining)
        if math.isfinite(remaining) and 0.0 <= remaining <= 1.0:
            self.latest_px4_battery_percent = remaining * 100.0
        else:
            self.latest_px4_battery_percent = math.nan

    def on_px4_global_position(self, msg: VehicleGlobalPosition):
        """Cache PX4 global position; altitude is AMSL in metres."""
        self.last_px4_global_position_monotonic = time.monotonic()
        if bool(msg.lat_lon_valid) and bool(msg.alt_valid):
            self.latest_px4_global_position = msg
        else:
            self.latest_px4_global_position = None

    def on_px4_local_position(self, msg: VehicleLocalPosition):
        """Cache PX4 local position for heading/yaw."""
        self.last_px4_local_position_monotonic = time.monotonic()
        if math.isfinite(float(msg.heading)):
            self.latest_px4_local_position = msg
        else:
            self.latest_px4_local_position = None

    def on_request_command(self, _req, resp):
        """Enable the reserve state machine; its timer handles wait/retry."""
        self.request_enabled = True
        if self.accepted:
            resp.success = True
            resp.message = 'Request enabled; UAV is already accepted by Dock'
            return resp

        # Thử ngay khi user kích request; timer tiếp tục wait/retry sau đó.
        self.request_dock_if_needed()
        resp.success = True
        resp.message = 'Dock request state machine enabled'
        return resp

    def request_dock_if_needed(self):
        """Wait for Dock and retry ReserveDock while request_enabled is true."""
        if self.accepted or not self.request_enabled:
            return

        now = time.time()

        # Request đang chạy thì chờ tối đa 3 giây trước khi cho phép retry.
        if self.request_in_flight and (now - self.last_request_time) < 3.0:
            return
# Check if the request has timed out
        if self.request_in_flight:
            self.get_logger().warn('Reserve request timeout, retrying...')
            self.request_in_flight = False
# Send ReserveDock request
        if not self.reserve_client.wait_for_service(timeout_sec=0.1):
            self.get_logger().warn('Waiting for reserve service...')
            return

        req = ReserveDock.Request()
        req.dock_id = self.dock_id
        req.uav_id = self.uav_id
        req.request_gps = True

        self.request_in_flight = True
        self.last_request_time = now

        if self.uav_state == UavStatus.IDLE:
            self.uav_state = UavStatus.REQUESTING_DOCK

        self.get_logger().info('Sending reserve request...')
        future = self.reserve_client.call_async(req)
        future.add_done_callback(self.on_reserve_response)

    def on_reserve_response(self, future):
        """
        ReserveDock response.
        Nếu response về tốt thì kích hoạt session.
        Nếu response không về, DockState vẫn xử lý được.
        """
        self.request_in_flight = False

        try:
            resp = future.result()
        except Exception as e:
            self.get_logger().error(f'Reserve request failed: {e}')
            return

        self.get_logger().info(
            f'Reserve response accepted={resp.accepted}, reason={resp.reason}'
        )

        if not resp.accepted:
            return

        # Update topic theo response của Dock.
        self.beacon_topic = resp.gps_topic
        self.contact_topic = resp.contact_topic

        self.activate_dock_session(reason='reserve_response accepted=true')

    def on_release_command(self, _req, resp):
        """Disable future reserve retries, then send ReleaseDock."""
        self.request_enabled = False
        if not self.release_client.wait_for_service(timeout_sec=0.1):
            resp.success = False
            resp.message = 'Dock release service is not available'
            return resp

        req = ReleaseDock.Request()
        req.dock_id = self.dock_id
        req.uav_id = self.uav_id
        future = self.release_client.call_async(req)
        future.add_done_callback(self.on_release_response)
        resp.success = True
        resp.message = 'ReleaseDock request sent; watch DockState for IDLE'
        return resp

    def on_release_response(self, future):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f'Release request failed: {exc}')
            return
        self.get_logger().info(
            f'Release response accepted={response.accepted}, reason={response.reason}'
        )

    def on_dock_state(self, msg: DockState):
        """
        DockState là nguồn xác nhận chính.

        Nếu Dock nói:
          state = RESERVED/CONTACTED
          reserved_uav_id = uav_01

        Thì UAV tự accepted=True.
        """
        if msg.dock_id != self.dock_id:
            return

        if msg.state == DockState.IDLE and self.accepted:
            self.accepted = False
            self.request_in_flight = False
            self.uav_state = UavStatus.IDLE
            self.get_logger().info('Dock released; UAV state -> IDLE')
            return

        if msg.reserved_uav_id != self.uav_id:
            return

        if msg.state in [DockState.RESERVED, DockState.CONTACTED]:
            self.activate_dock_session(
                reason=f'dock_state state={msg.state}, reserved={msg.reserved_uav_id}'
            )
            if msg.state == DockState.CONTACTED:
                self.uav_state = UavStatus.CONTACTED

    def activate_dock_session(self, reason: str):
        """
        Kích hoạt session với Dock.
        Hàm này chỉ tạo subscription một lần.
        """
        if not self.accepted:
            self.get_logger().info(f'Dock session activated: {reason}')

        self.accepted = True
        self.request_in_flight = False

        if self.uav_state in [UavStatus.IDLE, UavStatus.REQUESTING_DOCK]:
            self.uav_state = UavStatus.APPROACHING_DOCK

        if self.beacon_sub is None:
            self.beacon_sub = self.create_subscription(
                DockBeacon,
                self.beacon_topic,
                self.on_beacon,
                10,
            )
            self.get_logger().info(f'Subscribed beacon: {self.beacon_topic}')

        if self.contact_sub is None:
            self.contact_sub = self.create_subscription(
                DockContact,
                self.contact_topic,
                self.on_contact,
                10,
            )
            self.get_logger().info(f'Subscribed contact: {self.contact_topic}')

    def on_beacon(self, msg: DockBeacon):
        """
        Nhận DockBeacon:
          - Dock GPS
          - Dock state
        """
        gps = msg.gps
        now = time.monotonic()
        if (
            self.last_beacon_log_monotonic is None
            or now - self.last_beacon_log_monotonic >= self.heartbeat_log_period_s
        ):
            self.last_beacon_log_monotonic = now
            state = msg.state
            self.get_logger().info(
                f'[HEARTBEAT RX] DOCK GPS FULL\n'
                f'  identity: version={gps.interface_version} dock_id={gps.dock_id} '
                f'seq={gps.seq} stamp={gps.stamp_unix:.3f}\n'
                f'  position: lat={gps.latitude_deg:.7f} '
                f'lon={gps.longitude_deg:.7f} alt={gps.altitude_m:.3f}m\n'
                f'  velocity_ned: n={gps.vel_n_m_s:.3f} e={gps.vel_e_m_s:.3f} '
                f'd={gps.vel_d_m_s:.3f}m/s\n'
                f'  heading: deg={gps.heading_deg:.3f} valid={gps.heading_valid}\n'
                f'  quality: fix_type={gps.fix_type} eph={gps.eph_m:.3f}m '
                f'epv={gps.epv_m:.3f}m\n'
                f'  validity: gps_ok={gps.gps_ok} velocity={gps.velocity_valid}\n'
                f'  dock_state: version={state.interface_version} seq={state.seq} '
                f'stamp={state.stamp_unix:.3f} state={state.state} '
                f'available={state.available} reserved={state.reserved_uav_id} '
                f'gps_ok={state.gps_ok} hardware_ok={state.hardware_ok} '
                f'reason={state.reason}'
            )

    def on_contact(self, msg: DockContact):
        """
        Nhận contact từ Dock.
        """
        if not msg.valid:
            return
        if msg.dock_id != self.dock_id or msg.uav_id != self.uav_id:
            return

        contact = bool(msg.contact)
        if contact != self.last_contact_state:
            self.last_contact_state = contact
            self.get_logger().info(
                f'DockContact changed contact={contact}, sensor={msg.sensor_id}'
            )

        if contact and self.uav_state != UavStatus.CONTACTED:
            self.uav_state = UavStatus.CONTACTED
            self.get_logger().info('UAV state -> CONTACTED by DockContact')

    def publish_status(self):
        """
        Publish heartbeat/status của UAV.
        """
        msg = UavStatus()
        msg.interface_version = 1
        msg.uav_id = self.uav_id
        msg.dock_id = self.dock_id
        msg.seq = self.seq
        msg.stamp_unix = time.time()
        msg.uav_state = self.uav_state
        if self.is_px4_fresh(self.last_px4_battery_monotonic):
            msg.battery_percent = float(self.latest_px4_battery_percent)
        else:
            msg.battery_percent = math.nan
        msg.gps_ok = (
            self.is_px4_fresh(self.last_px4_global_position_monotonic)
            and self.latest_px4_global_position is not None
        )
        msg.accepted_by_dock = bool(self.accepted)

        self.status_pub.publish(msg)
        # Không log từng status heartbeat; Dock vẫn giám sát timeout.

        self.seq += 1

    def publish_gps(self):
        """Publish UAV GPS heartbeat, preferring PX4 DDS data when available."""
        if not self.accepted:
            return

        msg = UavGps()
        msg.interface_version = 2
        msg.uav_id = self.uav_id
        msg.seq = self.gps_seq
        msg.stamp_unix = time.time()

        px4_global_fresh = self.is_px4_fresh(
            self.last_px4_global_position_monotonic
        )
        px4_local_fresh = self.is_px4_fresh(self.last_px4_local_position_monotonic)
        px4_global = self.latest_px4_global_position if px4_global_fresh else None
        px4_local = self.latest_px4_local_position if px4_local_fresh else None

        if px4_global is None:
            msg.latitude_deg = math.nan
            msg.longitude_deg = math.nan
            msg.altitude_m = math.nan
            msg.eph_m = math.nan
            msg.epv_m = math.nan
            msg.gps_ok = False
        else:
            msg.latitude_deg = float(px4_global.lat)
            msg.longitude_deg = float(px4_global.lon)
            msg.altitude_m = float(px4_global.alt)
            msg.eph_m = float(px4_global.eph)
            msg.epv_m = float(px4_global.epv)
            # Khi đã có VehicleGlobalPosition hợp lệ từ PX4, mặc định xem GPS OK.
            msg.gps_ok = True

        if px4_local is None:
            msg.heading_deg = math.nan
        else:
            msg.heading_deg = math.degrees(float(px4_local.heading))

        self.gps_pub.publish(msg)
        # Không log từng GPS heartbeat; Dock log dữ liệu nhận theo chu kỳ.
        self.gps_seq += 1


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
