import time


def now_s() -> float:
    return time.time()


def access_key(root: str, dock_id: str) -> str:
    return f"{root}/dock/{dock_id}/access"


def dock_gps_key(root: str, dock_id: str, uav_id: str) -> str:
    return f"{root}/dock/{dock_id}/uav/{uav_id}/gps"


def uav_status_key(root: str, uav_id: str) -> str:
    return f"{root}/uav/{uav_id}/status"


def landing_key(root: str, uav_id: str) -> str:
    return f"{root}/uav/{uav_id}/landing"


def make_access_request(dock_id: str, uav_id: str) -> dict:
    return {
        "type": "access_request",
        "interface_version": 1,
        "dock_id": dock_id,
        "uav_id": uav_id,
        "stamp_unix": now_s(),
        "request": "reserve_dock",
    }


def make_access_response(dock_id: str, uav_id: str, accepted: bool, reason: str, dock_state: str) -> dict:
    return {
        "type": "access_response",
        "interface_version": 1,
        "dock_id": dock_id,
        "uav_id": uav_id,
        "stamp_unix": now_s(),
        "accepted": accepted,
        "reason": reason,
        "dock_state": dock_state,
    }


def make_dock_gps(dock_id: str, uav_id: str, seq: int, dock_state: str) -> dict:
    return {
        "type": "dock_gps",
        "interface_version": 1,
        "dock_id": dock_id,
        "uav_id": uav_id,
        "seq": seq,
        "stamp_unix": now_s(),
        "dock_state": dock_state,
        "gps": {
            "lat": 10.7760000,
            "lon": 106.7000000,
            "alt": 20.0,
            "heading": 0.0,
            "fix_type": 3,
            "gps_ok": True,
        },
    }


def make_uav_status(dock_id: str, uav_id: str, seq: int, uav_state: str) -> dict:
    return {
        "type": "uav_status",
        "interface_version": 1,
        "dock_id": dock_id,
        "uav_id": uav_id,
        "seq": seq,
        "stamp_unix": now_s(),
        "uav_state": uav_state,
        "battery_percent": 80.0,
        "gps_ok": True,
    }


def make_landing_complete(dock_id: str, uav_id: str) -> dict:
    return {
        "type": "landing_complete",
        "interface_version": 1,
        "dock_id": dock_id,
        "uav_id": uav_id,
        "stamp_unix": now_s(),
        "result": "success",
    }
