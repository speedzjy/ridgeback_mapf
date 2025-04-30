#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import threading

stationsList = [
    "starting_station",
    "infrared_spectrum",
    "libs",
    "high_flux_xrd_workstation",
    "high_flux_electrocatalysis_workstation",
    "raman_spectra",
    "muffle_station",
    "imbibition_workstation",
    "liquid_dispensing",
    "liquid_dispensing_1",
    "solid_dispensing",
    "solid_dispensing_1",
    "magnetic_stirring",
    "magnetic_stirring_1",
    "magnetic_stirring_2",
    "capping_station",
    "dryer_workstation",
    "dryer_workstation_1",
    "new_centrifugation",
    "new_centrifugation_screen",
    "photocatalysis_workstation",
    "photocatalysis_workstation_1",
    "uv_vis_charge",
    "uv_vis_uncharge",
    "flourescence",
    "gc",
    "storage_workstation",
    "multi_robots_exchange_workstation",
    "map_center",
    "charge_station_hf_0",
    "charge_station_hf_1",
    "manual_workstation",
    "ultrasonic_cleaner",
    "furnace_workstation",
    "spotting_workstation",
    "confecting_workstation",
]


class FakeNavigationIn(Node):
    def __init__(self):
        super().__init__("fake_navigation_in")
        self._namespace = self.get_namespace()

        self.publisher = self.create_publisher(String, f"obsNavigation_in", 10)
        self.create_subscription(
            String, "obsNavigation_out", self.feedback_callback, 10
        )

        # 手动循环发送指令
        threading.Thread(target=self.command_loop, daemon=True).start()

    def command_loop(self):
        while rclpy.ok():
            for index, item in enumerate(stationsList):
                print(f"{index}: {item}")

            char = input("\n输入工作站序号: ")
            nav_cmd = int(char) if char else 0
            destination = stationsList[nav_cmd]

            obsNavigation_in = {
                "id": "0001",
                "exper_no": "1",
                "stamp": "1212",
                "destination": destination,
                "action": "move",
            }

            navigation_in = String()
            navigation_in.data = json.dumps(
                obsNavigation_in, sort_keys=True, indent=4, separators=(",", ": ")
            )

            print("=============pub msg===============")
            print(navigation_in.data)
            time.sleep(1)
            print("============================")
            self.publisher.publish(navigation_in)

    def feedback_callback(self, msg):
        print("=============rev msg===============")
        print(msg.data)
        print("============================")


def main(args=None):
    rclpy.init(args=args)
    try:
        node = FakeNavigationIn()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
