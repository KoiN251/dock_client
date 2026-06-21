#!/usr/bin/env python3

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import yaml
import zenoh

sys.path.insert(0, str(Path(__file__).resolve().parent / "common"))

from protocol import (
    access_key,
    dock_gps_key,
    uav_status_key,
    landing_key,
    make_access_request,
    make_uav_status,
    make_landing_complete,
)


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_zenoh_config(listen: str | None, connect: str | None):
    conf = zenoh.Config()

    try:
        conf.insert_json5("mode", '"peer"')

        if listen:
            conf.insert_json5("listen/endpoints", json.dumps([listen]))

        if connect:
            conf.insert_json5("connect/endpoints", json.dumps([connect]))

    except Exception as e:
        print(f"[WARN] Could not apply explicit Zenoh config: {e}")
        print("[WARN] Falling back to default Zenoh config")

    return conf


class UavNode:
    def __init__(self, cfg: dict):
        self.cfg = cfg

        self.root = cfg["zenoh"]["root"]
        self.uav_id = cfg["uav"]["id"]
        self.dock_id = cfg["dock"]["target_id"]
        self.heartbeat_hz = float(cfg["heartbeat"]["publish_hz"])

        self.accepted = False
        self.uav_state = "IDLE"
        self.seq = 0

    def on_dock_gps(self, sample):
        try:
            msg = json.loads(sample.payload.to_string())
        except Exception as e:
            print(f"[UAV] bad dock GPS: {e}")
            return

        gps = msg.get("gps", {})
        dock_state = msg.get("dock_state", "")

        print(
            f"[UAV] dock_gps seq={msg.get('seq')} "
            f"state={dock_state} "
            f"lat={gps.get('lat')} lon={gps.get('lon')} alt={gps.get('alt')}"
        )

    def request_dock(self, session):
        key = access_key(self.root, self.dock_id)
        req = make_access_request(self.dock_id, self.uav_id)

        print(f"[UAV] request dock access: {key}")
        replies = session.get(key, payload=json.dumps(req), timeout=3.0)

        got_reply = False

        for reply in replies:
            got_reply = True
            try:
                resp = json.loads(reply.ok.payload.to_string())
            except Exception as e:
                print(f"[UAV] bad access response: {e}")
                continue

            print(f"[UAV] access response: {resp}")

            if resp.get("accepted"):
                self.accepted = True
                self.uav_state = "APPROACHING_DOCK"
                return True

        if not got_reply:
            print("[UAV] no access response")

        return False

    def input_loop(self, landing_pub):
        print("")
        print("[UAV] Commands:")
        print("  l = send landing complete")
        print("  q = quit")
        print("")

        while True:
            cmd = input("[UAV] > ").strip().lower()

            if cmd == "l":
                msg = make_landing_complete(self.dock_id, self.uav_id)
                landing_pub.put(json.dumps(msg))
                self.uav_state = "LANDED"
                print("[UAV] sent landing complete")

            elif cmd == "q":
                print("[UAV] quit")
                raise SystemExit

            else:
                print("[UAV] unknown command")

    def run(self, listen: str | None, connect: str | None):
        conf = make_zenoh_config(listen, connect)

        print("[UAV] Opening Zenoh session...")
        print(f"[UAV] uav_id={self.uav_id}, target_dock_id={self.dock_id}")

        with zenoh.open(conf) as session:
            gps_k = dock_gps_key(self.root, self.dock_id, self.uav_id)
            status_k = uav_status_key(self.root, self.uav_id)
            landing_k = landing_key(self.root, self.uav_id)

            print(f"[UAV] subscribe dock GPS: {gps_k}")
            sub_gps = session.declare_subscriber(gps_k, self.on_dock_gps)

            print(f"[UAV] publish status: {status_k}")
            status_pub = session.declare_publisher(status_k)

            print(f"[UAV] publish landing: {landing_k}")
            landing_pub = session.declare_publisher(landing_k)

            ok = self.request_dock(session)

            if not ok:
                print("[UAV] dock access rejected or timeout")
                print("[UAV] still running subscriber, but heartbeat disabled")

            threading.Thread(target=self.input_loop, args=(landing_pub,), daemon=True).start()

            period = 1.0 / self.heartbeat_hz

            while True:
                if self.accepted:
                    msg = make_uav_status(
                        self.dock_id,
                        self.uav_id,
                        self.seq,
                        self.uav_state,
                    )
                    status_pub.put(json.dumps(msg))
                    print(f"[UAV] heartbeat seq={self.seq} state={self.uav_state}")
                    self.seq += 1

                time.sleep(period)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/uav.yaml")
    parser.add_argument("--listen", default=None, help="Example: tcp/0.0.0.0:7448")
    parser.add_argument("--connect", default=None, help="Example: tcp/100.87.x.x:7447")
    args = parser.parse_args()

    cfg = load_yaml(args.config)
    UavNode(cfg).run(args.listen, args.connect)


if __name__ == "__main__":
    main()
