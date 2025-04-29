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
from tf_transformations import quaternion_matrix, euler_from_quaternion, quaternion_from_euler
from scipy.spatial.transform import Rotation

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

import tf2_ros
import tf2_geometry_msgs

from std_msgs.msg import String, Bool, Int8, Int32
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist, Quaternion

from nav2_msgs.action import NavigateToPose


conflict_distence = 5.0
max_wait_try_times = 5


def load_station_pose_json(file_json_name):
    try:
        with open(os.path.expanduser(file_json_name), "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Opening {file_json_name} failed")
        return None

    station_pose = {}
    for item in data:
        pose = item.get("pose", {})
        if "ox" in pose:
            station_pose[item["name"]] = {
                "x": float(pose["x"]),
                "y": float(pose["y"]),
                "z": float(pose["z"]),
                "ox": float(pose["ox"]),
                "oy": float(pose["oy"]),
                "oz": float(pose["oz"]),
                "ow": float(pose["ow"]),
            }
        else:
            station_pose[item["name"]] = {
                "x": float(pose["x"]),
                "y": float(pose["y"]),
                "z": float(pose["z"]),
                "w": float(pose["w"]),
            }

    return station_pose


class PlatformCommunication:
    def __init__(
        self,
        host_ip,
        robot_name,
        pose_topic,
        station_pose_path,
        camera_pose_path,
        aruco_id,
        use_prefix=False,
    ):
        # launch文件的传入参数
        self.station_pose_path = station_pose_path

        # 机器人名称
        self.robot_prefix = robot_name if use_prefix else ""
        self.base_link_frame = (
            robot_name + "/base_link" if use_prefix else "hf_base_link"
        )

        self.robot_name = robot_name
        self.pose_topic = pose_topic

        # 充电站名称
        self.charge_station = "charge_station_" + self.robot_name

        # 底盘当前状态
        self.platform_status = defaultdict()
        self.platform_status["id"] = ""
        self.platform_status["exper_no"] = ""
        self.platform_status["stamp"] = rospy.Time.now().to_time()
        self.platform_status["state"] = "idle"
        self.platform_status["detail"] = ""
        self.platform_status["cur_station"] = "charge_station"

        self.global_status = defaultdict(dict)
        self.pub_global_status_msg = rospy.Publisher(
            self.robot_prefix + "/global_robots_status", String, queue_size=2
        )
        self.init_flag = False

        # 机械臂复位指令
        self.oper_reset_msg = {
            "id": "",
            "destination": "",
            "operations": [{"operation": "reset"}],
        }
        self.oper_pub = rospy.Publisher(
            self.robot_prefix + "/obsOperation_in", String, queue_size=10
        )

        # 当前位姿信息
        self.cur_location = PoseWithCovarianceStamped()
        self.cur_yaw = 0
        # 当前目标站点信息
        self.cur_station_name = ""
        # 上一个站点信息(从哪个站点出发)
        # 根据从哪个站点出发，需要的起始横移不同
        self.last_station_name = "map_center"

        # move_base client
        self.ac = actionlib.SimpleActionClient(
            self.robot_prefix + "/move_base", MoveBaseAction
        )
        # 当前move_base goal
        self.cur_goal = MoveBaseGoal()

        # 订阅话题
        # 订阅 task_manager 的目标站指令
        self.sub_dms_cmd = rospy.Subscriber(
            self.robot_prefix + "/obsNavigation_in",
            String,
            self.dms_callback,
            buff_size=10,
        )
        # 订阅 amcl 的当前位姿
        self.sub_amcl_pose = rospy.Subscriber(
            self.robot_prefix + self.pose_topic,
            PoseWithCovarianceStamped,
            self.amcl_pose_callback,
            queue_size=1,
        )

        # 发布话题
        # 发送给 task_manager , 到达目标站的反馈
        self.pub_dms_msg = rospy.Publisher(
            self.robot_prefix + "/obsNavigation_out", String, queue_size=10
        )

        # 记录amcl_pose获取时间
        self.amcl_pose_time = rospy.Time.now()

        # 全部站点坐标文件
        self.station_pose = load_station_pose_json(self.station_pose_path)

        # 表示当前接收到了新目标点，正在移动状态
        self.state_move = False
        self.state_move_lock = threading.Lock()

        self.last_action = ""

        self.loop_rate = rospy.Rate(10)

        # 这个线程专门接收mapf后端发来的move_base.goal消息
        self.thread1 = threading.Thread(target=self.run_to_goal)
        self.thread1.start()

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
        self.amcl_pose_time = rospy.Time.now()

        # 发送给flask服务器
        pose = pos.pose.pose
        # 组装 pose 信息
        pose_dict = {
            "robot_name": self.robot_name,
            "status": self.platform_status["state"],
            "stamp": self.amcl_pose_time.to_sec(),
            "position": {
                "x": pose.position.x,
                "y": pose.position.y,
                "z": pose.position.z,
            },
            "orientation": {
                "x": pose.orientation.x,
                "y": pose.orientation.y,
                "z": pose.orientation.z,
                "w": pose.orientation.w,
            },
        }

    # 将当前机器人目标站位置发送给flask服务器
    def dms_callback(self, msg):
        # 接收到第一帧指令时，初始化成功
        self.init_flag = True

        cmd = json.loads(msg.data)

        pprint(cmd)
        rospy.loginfo(
            f"\033[1;32m做任何操作前机械臂复位\033[0m, 复位工作站{self.last_station_name}"
        )
        if "charge_station" in self.last_station_name:
            self.oper_reset_msg["destination"] = "charge_station"
        else:
            self.oper_reset_msg["destination"] = self.last_station_name
        self.oper_pub.publish(String(json.dumps(self.oper_reset_msg)))

        # 获取JSON中的值
        action = cmd["action"]
        dest_station = cmd["destination"]

        self.last_action = action

        # 更新platform_status_
        self.platform_status["id"] = cmd["id"]

        if action == "move" or action == "charge":
            rospy.loginfo(f"Action = \033[1;32m{action}\033[0m")
            if action == "move" and self.recharge_flag:
                self.platform_status["state"] = "idle"
                self.platform_status["detail"] = "移动前解除充电"
                pub_msg = String()
                pub_msg.data = json.dumps(self.platform_status)
                self.loop_rate.sleep()
                self.pub_dms_msg.publish(pub_msg)
                self.platform_status["state"] = "charging"
                return

            rospy.loginfo("\033[0;33m等待2s让避让状态更新\033[0m")
            rospy.sleep(2.0)

            # 保存当前目标站点信息
            self.cur_station_name = dest_station

            # 每次运行重新加载站点信息进行更新
            self.station_pose = load_station_pose_json(self.station_pose_path)

            # 以 move_base 格式保存当前目标站点位姿
            self.cur_goal.target_pose.header.frame_id = "map"
            self.cur_goal.target_pose.header.stamp = rospy.Time.now()

            station = self.station_pose[dest_station]
            self.cur_goal.target_pose.pose.position.x = station["x"]
            self.cur_goal.target_pose.pose.position.y = station["y"]
            self.cur_goal.target_pose.pose.orientation.z = station["z"]
            self.cur_goal.target_pose.pose.orientation.w = station["w"]

            self.platform_status["state"] = "running"
            self.platform_status["detail"] = "底盘前往" + dest_station

            # 等待1s用于amcl_pose回调函数修改底盘running状态
            rospy.sleep(rospy.Duration(1.0))

            # 每次接收到新目标地点，进行微调操作
            # 先发给mapf后端，给mapf计算时间
            self.send_goal_to_flask()

            # 微调前先中止移动状态，使运动线程停止
            # with self.state_move_lock:
            self.state_move = False

            # 停止move_base运动线程
            rospy.loginfo("停止move_base运动线程...")
            self.ac.cancel_goal()
            rospy.sleep(0.2)

            # 先后退0.2m
            rospy.loginfo("调整姿态以方便去下一个工作站...")

            self.stroll_to_back((0, 0.3))

            rospy.loginfo("横移完毕, 原地旋转为终点姿态")

            # 停止之前的move_base运动线程
            self.ac.cancel_goal()
            # 原地旋转为终点姿态
            (_, _, yaw) = euler_from_quaternion(
                (
                    self.cur_goal.target_pose.pose.orientation.x,
                    self.cur_goal.target_pose.pose.orientation.y,
                    self.cur_goal.target_pose.pose.orientation.z,
                    self.cur_goal.target_pose.pose.orientation.w,
                )
            )
            self.rotate_in_place(yaw)
            rospy.loginfo("原地旋转完毕")
            self.ac.cancel_goal()

            # 设置为移动状态
            with self.state_move_lock:
                self.state_move = True

            self.last_station_name = self.cur_station_name
        else:
            pass

        return

    def rotate_in_place(self, yaw):
        tmp_goal = MoveBaseGoal()
        tmp_goal.target_pose.header.frame_id = "map"
        tmp_goal.target_pose.header.stamp = rospy.Time.now()
        tmp_goal.target_pose.pose.position = self.cur_location.pose.pose.position
        tmp_goal.target_pose.pose.orientation = Quaternion(
            *quaternion_from_euler(0, 0, yaw)
        )

        while not rospy.is_shutdown():
            # 计算当前机器人方向与目标方向的差异
            curr_goal_orientate_difference = math.fabs(self.cur_yaw - yaw)

            # 如果差异小于 5° 或大于 355°，则停止发送命令
            if (
                curr_goal_orientate_difference < 5 * math.pi / 180
                or curr_goal_orientate_difference > 355 * math.pi / 180
            ):
                break

            # 发送移动命令并等待结果
            self.ac.send_goal(tmp_goal)
            self.ac.wait_for_result()
            rospy.loginfo("Wait for inplace-rotate")
            if self.ac.get_state() == actionlib.GoalStatus.ABORTED:
                rospy.logwarn("原地旋转 STATE: Reach Goal ABORTED, Resend Goal")
                self.ac.cancel_goal()
            elif self.ac.get_state() == actionlib.GoalStatus.SUCCEEDED:
                break

    # 先发送全局目标位置给flask后端，然后一步步接受move_base的目标点
    def send_goal_to_flask(self):
        # 将目标位置发送给flask服务器
        pass

    # 用于往hf_base_link的x轴和y轴方向移动distance距离，由于机械臂在站点一侧
    # 往y轴方向偏移看起来就是"后退"(远离站点)
    def stroll_to_back(self, x_distance, y_distance):
        # 相对于base_link的偏移目标点
        pose_transform = tf2_geometry_msgs.PoseStamped()
        pose_transform.header.frame_id = self.base_link_frame
        pose_transform.pose.position.x = x_distance
        pose_transform.pose.position.y = y_distance
        pose_transform.pose.position.z = 0
        pose_transform.pose.orientation.x = 0
        pose_transform.pose.orientation.y = 0
        pose_transform.pose.orientation.z = 0
        pose_transform.pose.orientation.w = 1

        # 将该点转化到map下
        pose_transform_map = tf2_geometry_msgs.PoseStamped()

        buffer = tf2_ros.Buffer()
        listener = tf2_ros.TransformListener(buffer)
        transform_flag = False

        while not transform_flag:
            try:
                # 尝试进行坐标系变换
                pose_transform_map = buffer.transform(
                    pose_transform, "map", rospy.Duration(0)
                )
                transform_flag = True
            except tf2_ros.TransformException as e:
                # 如果出现异常，打印信息并继续等待
                rospy.loginfo("wait tf buffer listener.....")
                rospy.sleep(1.0)

        self.stroll_a_little(pose_transform_map)

    # 往pose_transform_map点挪动
    def stroll_a_little(self, pose_transform_map):
        tmp_goal = MoveBaseGoal()
        tmp_goal.target_pose.header.frame_id = "map"
        tmp_goal.target_pose.header.stamp = rospy.Time.now()
        tmp_goal.target_pose.pose.position.x = pose_transform_map.pose.position.x
        tmp_goal.target_pose.pose.position.y = pose_transform_map.pose.position.y
        tmp_goal.target_pose.pose.position.z = pose_transform_map.pose.position.z
        tmp_goal.target_pose.pose.orientation = pose_transform_map.pose.orientation

        while not rospy.is_shutdown():
            self.ac.send_goal(tmp_goal)
            self.ac.wait_for_result()
            if self.ac.get_state() == actionlib.GoalStatus.ABORTED:
                rospy.logwarn("挪动 STATE: Reach Goal ABORTED, Resend Goal")
                self.ac.cancel_goal()
            elif self.ac.get_state() == actionlib.GoalStatus.SUCCEEDED:
                break

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
                        rospy.loginfo("%s发送step目标位置", self.robot_name)

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
                                self.robot_name,
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
                            f"{self.robot_name}: \033[1;32m Reach Goal SUCCEEDED\033[0m"
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


def main():
    # 清除 ROS 特有的命令行参数
    argv = rospy.myargv(argv=sys.argv)

    parser = argparse.ArgumentParser(
        description="Platform Communication Node Parameters"
    )
    parser.add_argument("-aruco_id", type=str, default="1", help="ArUco ID")
    parser.add_argument(
        "-station_pose_path", type=str, required=True, help="Station pose file path"
    )

    args = parser.parse_args(argv[1:])

    # 初始化 ROS 节点
    rospy.init_node("platform_communication_node")
    robot_name = rospy.get_param("~robot_name", default="hf_0")
    pose_topic = rospy.get_param("~pose_topic", default="/amcl_pose_tf")
    host_ip = rospy.get_param("~host_ip", default="192.168.1.170")
    debug = rospy.get_param("~debug", default="false")

    use_prefix = True if debug == True else False

    pc = PlatformCommunication(
        host_ip=host_ip,
        robot_name=robot_name,
        pose_topic=pose_topic,
        station_pose_path=args.station_pose_path,
        camera_pose_path=args.camera_pose_path,
        aruco_id=args.aruco_id,
        use_prefix=use_prefix,
    )
    rospy.spin()


if __name__ == "__main__":
    main()
