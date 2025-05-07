#!/usr/bin/env python3
import argparse
import json
import threading
import sys
import math
import copy
import requests
import os
from collections import defaultdict
from pprint import pprint

import numpy as np
from tf_transformations import (
    quaternion_matrix,
    euler_from_quaternion,
    quaternion_from_euler,
)
from scipy.spatial.transform import Rotation

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

import tf2_ros
import tf2_geometry_msgs

from std_msgs.msg import String, Bool, Int8, Int32
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist, Quaternion

from nav2_msgs.action import NavigateToPose

from rclpy.task import Future

conflict_distence = 5.0
max_wait_try_times = 5


def load_station_pose_json(file_json_name):
    try:
        with open(os.path.expanduser(file_json_name), "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Opening {file_json_name} failed")
        return None


class PlatformCommunication(Node):
    def __init__(self, station_pose_path):
        super().__init__("platform_communication_node")
        self._namespace = self.get_namespace()
        self._robot_name = self._namespace

        self._action_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._goal_handle = None
        self._send_goal_future = None

        self._base_link_frame = f"{self._robot_name}/base_link"

        # 底盘当前状态
        self.platform_status = defaultdict()
        self.platform_status["id"] = ""
        self.platform_status["expr_no"] = ""
        self.platform_status["stamp"] = ""
        self.platform_status["state"] = "idle"
        self.platform_status["cur_station"] = "parking_station"

        # 当前位姿信息
        self.cur_yaw = None
        self.cur_location = PoseWithCovarianceStamped()

        # 当前move_base goal
        self.cur_goal = NavigateToPose.Goal()

        # 订阅 task_manager 的目标站指令
        self.sub_dms_cmd = self.create_subscription(
            String, "obsNavigation_in", self.dms_callback, 10  # QoS 队列长度
        )

        # 订阅 amcl 的当前位姿
        self.sub_amcl_pose = self.create_subscription(
            PoseWithCovarianceStamped, "amcl_pose_tf", self.amcl_pose_callback, 1
        )

        # 发布话题：发送给 task_manager 的反馈信息
        self.pub_dms_msg = self.create_publisher(String, "obsNavigation_out", 10)

        # 全部站点坐标文件
        self.station_pose_path = station_pose_path
        self.station_pose = load_station_pose_json(self.station_pose_path)

        # 表示当前接收到了新目标点，正在移动状态
        self.state_move = False
        self.state_move_lock = threading.Lock()

        self.last_action = ""

        self.loop_rate = self.create_rate(10)

        # 这个线程专门接收mapf后端发来的move_base.goal消息
        # self.thread1 = threading.Thread(target=self.run_to_goal)
        # self.thread1.start()

    # 实时储存位姿, 并发送给flask服务器
    def amcl_pose_callback(self, pos):
        # 实时储存位姿
        self.cur_location = pos
        (_, _, self.cur_yaw) = euler_from_quaternion(
            (
                pos.pose.pose.orientation.x,
                pos.pose.pose.orientation.y,
                pos.pose.pose.orientation.z,
                pos.pose.pose.orientation.w,
            )
        )

    # 将当前机器人目标站位置发送给flask服务器
    def dms_callback(self, msg):
        cmd = json.loads(msg.data)
        pprint(cmd)

        # 获取JSON中的值
        action = cmd["action"]
        dest_station = cmd["destination"]

        self.last_action = action

        # 更新platform_status_
        self.platform_status["id"] = cmd["id"]

        if action == "move":
            self.get_logger().info(f"Destination: \033[1;32m{dest_station}\033[0m")

            # 保存当前目标站点信息
            self.cur_station_name = dest_station

            # 每次运行重新加载站点信息进行更新
            self.station_pose = load_station_pose_json(self.station_pose_path)

            # 以 move_base 格式保存当前目标站点位姿
            self.cur_goal.pose = PoseStamped()
            self.cur_goal.behavior_tree = ""
            self.cur_goal.pose.header.frame_id = "map"
            self.cur_goal.pose.header.stamp = self.get_clock().now().to_msg()

            station = self.station_pose[dest_station]
            self.cur_goal.pose.pose.position.x = float(station["x"])
            self.cur_goal.pose.pose.position.y = float(station["y"])
            self.cur_goal.pose.pose.orientation.z = float(station["z"])
            self.cur_goal.pose.pose.orientation.w = float(station["w"])

            self._action_client.wait_for_server()

            self.platform_status["state"] = "running"
            self.last_station_name = self.cur_station_name
            self.get_logger().info(f"Sending goal to: \033[1;32m{dest_station}\033[0m")

            if self._send_goal_future is not None:
                self._send_goal_future.cancel()
                self.loop_rate.sleep()

            self._send_goal_future = self._action_client.send_goal_async(self.cur_goal)
            self._send_goal_future.add_done_callback(self.goal_response_callback)

        else:
            pass

        return

    def goal_response_callback(self, future: Future):
        self._goal_handle = future.result()
        if not self._goal_handle.accepted:
            self.get_logger().info("Goal rejected :(")
            return

        self.get_logger().info("Goal accepted :)")

        self._get_result_future = self._goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future: Future):
        result = future.result()
        self.platform_status.update({"state": "done", "cur_station": self.cur_station_name})
        self.pub_dms_msg.publish(String(data=json.dumps(self.platform_status)))
        self.get_logger().info(f"\033[1;32m{self.cur_station_name}\033[0m reached :)")

    # 先发送全局目标位置给flask后端，然后一步步接受move_base的目标点
    def send_goal_to_flask(self):
        # 将目标位置发送给flask服务器
        pass

    # 正常请求终点的goal线程：self.state_move == True
    # 一步步接受move_base的目标点
    # 如果move_base state为success并且到达全局(非局部)目标点，发布到达消息
    def run_to_goal(self):
        while not rospy.is_shutdown():
            with self.state_move_lock:
                if self.state_move == True:
                    try:
                        response = self.session.get(self.host_ip + "/mapf_goal")
                    except:
                        # rospy.logwarn("FUNC run to goal: 无法连接flask_core服务器")
                        continue

                    robot_goal = json.loads(response.text)
                    # 如果当前有goal, 发布move_base_goal
                    if robot_goal:
                        goal = MoveBaseGoal()
                        goal.target_pose.header.frame_id = "map"
                        goal.target_pose.header.stamp = rospy.Time.now()
                        goal.target_pose.pose.position.x = robot_goal["position"]["x"]
                        goal.target_pose.pose.position.y = robot_goal["position"]["y"]
                        goal.target_pose.pose.position.z = robot_goal["position"]["z"]
                        goal.target_pose.pose.orientation.x = robot_goal["orientation"][
                            "x"
                        ]
                        goal.target_pose.pose.orientation.y = robot_goal["orientation"][
                            "y"
                        ]
                        goal.target_pose.pose.orientation.z = robot_goal["orientation"][
                            "z"
                        ]
                        goal.target_pose.pose.orientation.w = robot_goal["orientation"][
                            "w"
                        ]

                        self.ac.send_goal(goal)
                        self.ac.wait_for_result(rospy.Duration(1.0))
                        rospy.loginfo("%s发送step目标位置", self._robot_name)

                        dis_to_goal = (
                            self.cur_goal.target_pose.pose.position.x
                            - self.cur_location.pose.pose.position.x
                        ) ** 2 + (
                            self.cur_goal.target_pose.pose.position.y
                            - self.cur_location.pose.pose.position.y
                        ) ** 2
                        dis_to_goal = math.sqrt(dis_to_goal)

                        if (
                            dis_to_goal > 0.4
                            and self.ac.get_state() != actionlib.GoalStatus.ACTIVE
                        ):
                            rospy.loginfo(
                                "%s任务规划挂起, 临时进入直接规划模式, 当前离目标点距离: %.2f",
                                self._robot_name,
                                dis_to_goal,
                            )
                            self.ac.cancel_goal()
                            rospy.sleep(0.5)
                            final_goal = MoveBaseGoal()
                            final_goal.target_pose.header.frame_id = "map"
                            final_goal.target_pose.header.stamp = rospy.Time.now()
                            final_goal.target_pose.pose.position = (
                                self.cur_goal.target_pose.pose.position
                            )
                            final_goal.target_pose.pose.orientation = (
                                self.cur_goal.target_pose.pose.orientation
                            )
                            self.ac.send_goal(final_goal)
                            self.ac.wait_for_result(rospy.Duration(2))

                    # 检查是否到达终点
                    dis_to_goal = (
                        self.cur_goal.target_pose.pose.position.x
                        - self.cur_location.pose.pose.position.x
                    ) ** 2 + (
                        self.cur_goal.target_pose.pose.position.y
                        - self.cur_location.pose.pose.position.y
                    ) ** 2
                    dis_to_goal = math.sqrt(dis_to_goal)

                    # rospy.loginfo(self.ac.get_state())

                    if (
                        self.ac.get_state() == actionlib.GoalStatus.SUCCEEDED
                        and dis_to_goal <= 0.2
                    ):
                        rospy.loginfo(
                            f"{self._robot_name}: \033[1;32m Reach Goal SUCCEEDED\033[0m"
                        )
                        self.state_move = False

                        # 如果不是充电站
                        if "charge_station" not in self.cur_station_name:
                            self.platform_status.update(
                                {
                                    "state": "done",
                                    "detail": "底盘已运动到 " + self.cur_station_name,
                                }
                            )
                            # 主动发布话题
                            self.pub_dms_msg.publish(
                                String(data=json.dumps(self.platform_status))
                            )
                            self.platform_status["state"] = "idle"
                        elif self.last_action == "charge":
                            # 如果是充电站，到达后进行微调
                            rospy.loginfo("该站为充电站，到达后进行微调:")
                            self.loop_rate.sleep()
                            # 微调：x, y方向一起平移
                            rospy.loginfo("微调: x, y方向一起平移")
                            for i in range(1, 6):
                                flag_get_camera_tran, trans_map = self.get_camera_tran(
                                    i / 5.0
                                )
                                while not flag_get_camera_tran:
                                    rospy.loginfo("获取相机位置失败,每隔2s重新检测...")
                                    rospy.sleep(2)
                                    flag_get_camera_tran, trans_map = (
                                        self.get_camera_tran(i / 5.0)
                                    )
                                trans_map.pose.position.z = 0
                                self.stroll_a_little(trans_map)
                                self.loop_rate.sleep()

                            with self.recharge_lock:
                                self.recharge_flag = True

                            # 发布充电命令
                            charging_thread = threading.Thread(target=self.recharging)
                            charging_thread.start()
                            self.loop_rate.sleep()

                            self.platform_status.update(
                                {"state": "done", "detail": "底盘已运动到充电桩"}
                            )
                            self.pub_dms_msg.publish(
                                String(data=json.dumps(self.platform_status))
                            )
                            self.platform_status["state"] = "charging"

            rospy.sleep(0.5)


def main(args=None):
    rclpy.init(args=args)

    # 使用 rclpy 的参数处理来兼容 --ros-args
    parser = argparse.ArgumentParser(
        description="Platform Communication Node Parameters", allow_abbrev=False
    )
    parser.add_argument(
        "--path", type=str, required=True, help="Path to the station pose file"
    )
    parsed_args, _ = parser.parse_known_args()  # 忽略 ROS 2 的参数，比如 --ros-args

    pc = PlatformCommunication(station_pose_path=parsed_args.path)

    try:
        rclpy.spin(pc)
    except KeyboardInterrupt:
        pass
    finally:
        pc.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
