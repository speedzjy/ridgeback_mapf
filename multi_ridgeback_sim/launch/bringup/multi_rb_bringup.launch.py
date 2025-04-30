# Copyright 2023 Clearpath Robotics, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @author Roni Kreinin (rkreinin@clearpathrobotics.com)

import copy, os
from datetime import datetime

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    GroupAction,
    TimerAction,
    RegisterEventHandler,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit

from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
    TextSubstitution,
)

from launch_ros.actions import PushRosNamespace, Node
from launch_ros.substitutions import FindPackageShare

from clearpath_config.clearpath_config import ClearpathConfig


ARGUMENTS = [
    DeclareLaunchArgument(
        "world", default_value="warehouse", description="Gazebo World"
    ),
    DeclareLaunchArgument(
        "bringup_setup_path",
        default_value=[EnvironmentVariable("HOME"), "/clearpath/"],
        description="Clearpath setup path",
    ),
    DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        choices=["true", "false"],
        description="use_sim_time",
    ),
]


ROBOT_LIST = [
    {"name": "rb_0", "x": "0.0", "y": "0.0", "z": "0.3", "yaw": "0.0"},
    {"name": "rb_1", "x": "2.0", "y": "0.0", "z": "0.3", "yaw": "0.0"},
    # {"name": "rb_2", "x": "4.0", "y": "0.0", "z": "0.3", "yaw": "0.0"},
    # {"name": "rb_3", "x": "-2.0", "y": "0.0", "z": "0.3", "yaw": "0.0"},
    # {"name": "rb_4", "x": "-4.0", "y": "0.0", "z": "0.3", "yaw": "0.0"},
]


def launch_setup(context, *args, **kwargs):
    # Directories
    pkg_clearpath_gz = get_package_share_directory("multi_ridgeback_sim")

    # ign gazebo
    gz_sim_launch = PathJoinSubstitution(
        [pkg_clearpath_gz, "launch/bringup", "gz_sim.launch.py"]
    )
    gz_sim_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([gz_sim_launch]),
        launch_arguments=[("world", LaunchConfiguration("world"))],
    )

    last_action = None
    actions = []
    actions.extend([gz_sim_cmd])

    delay_after_gz_sim = 5.0
    delay_between_robots = 5.0
    delay_spawn_robot = 1.0
    delay_laser_tools = 3.0
    for robot_index, robot in enumerate(ROBOT_LIST):
        single_robot_path = PathJoinSubstitution(
            [LaunchConfiguration("bringup_setup_path"), robot["name"]]
        )

        world = LaunchConfiguration("world")
        x, y, z, yaw = (
            TextSubstitution(text=robot["x"]),
            TextSubstitution(text=robot["y"]),
            TextSubstitution(text=robot["z"]),
            TextSubstitution(text=robot["yaw"]),
        )

        # clearpath config
        clearpath_config = ClearpathConfig(
            os.path.join(str(single_robot_path.perform(context)), "robot.yaml")
        )
        namespace = clearpath_config.system.namespace
        robot_name = "robot" if namespace in ("", "/") else namespace + "/robot"

        # spawn robot
        launch_file_platform_service = PathJoinSubstitution(
            [single_robot_path, "platform/launch", "platform-service.launch.py"]
        )
        launch_file_sensors_service = PathJoinSubstitution(
            [single_robot_path, "sensors/launch", "sensors-service.launch.py"]
        )
        launch_file_manipulators_service = PathJoinSubstitution(
            [single_robot_path, "manipulators/launch", "manipulators-service.launch.py"]
        )

        group_action_spawn_param = GroupAction(
            [
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource([launch_file_platform_service]),
                    launch_arguments=[
                        (
                            "prefix",
                            [
                                "/world/",
                                world,
                                "/model/",
                                robot_name,
                                "/link/base_link/sensor/",
                            ],
                        )
                    ],
                ),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource([launch_file_sensors_service]),
                    launch_arguments=[
                        (
                            "prefix",
                            [
                                "/world/",
                                world,
                                "/model/",
                                robot_name,
                                "/link/base_link/sensor/",
                            ],
                        )
                    ],
                ),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource([launch_file_manipulators_service]),
                ),
            ]
        )

        spawn_robot = Node(
            package="ros_gz_sim",
            executable="create",
            namespace=namespace,
            arguments=[
                "-name",
                robot_name,
                "-x",
                x,
                "-y",
                y,
                "-z",
                z,
                "-Y",
                yaw,
                "-topic",
                "robot_description",
            ],
            output="screen",
        )

        # 位姿映射
        pose_bridge = Node(
            namespace=namespace,
            package="ros_gz_bridge",
            executable="parameter_bridge",
            name=f"pose_bridge",
            output="screen",
            arguments=[
                f"/model/{namespace}/robot/pose@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V"
            ],
            remappings=[(f"/model/{namespace}/robot/pose", f"/{namespace}/ign_tf")],
        )

        # tf relay
        node_tf2_relay = Node(
            namespace=namespace,
            package="multi_ridgeback_sim",
            executable="tf_namespace_relay",
            name="tf_namespace_relay",
            output="screen",
        )

        # scan frame relay
        node_scan_relay = Node(
            namespace=namespace,
            package="multi_ridgeback_sim",
            executable="scan_frame_relay",
            name="scan_frame_relay",
            output="screen",
        )

        # ira_laser_tools
        launch_file_ira_laser_tools = PathJoinSubstitution(
            [
                FindPackageShare("ira_laser_tools"),
                "launch",
                "laserscan_multi_merger.launch.py",
            ]
        )
        launch_ira_laser_tools_cmd = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([launch_file_ira_laser_tools]),
            launch_arguments=[("namespace", namespace)],
        )

        append_nodes = [
            pose_bridge,
            node_scan_relay,
            node_tf2_relay,
            launch_ira_laser_tools_cmd,
        ]

        if robot_index == 0:
            event_spawn_robot = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=spawn_robot,
                    on_exit=[
                        TimerAction(
                            period=delay_laser_tools,  # 3.0
                            actions=append_nodes,
                        ),
                    ],
                )
            )

            # 启动gazebo后过delay_after_gz_sim秒后加载参数
            # 加载参数过1s spwan robot
            actions.extend(
                [
                    TimerAction(
                        period=delay_after_gz_sim,  # 5.0
                        actions=[
                            group_action_spawn_param,
                            TimerAction(
                                period=delay_spawn_robot,  # 1.0
                                actions=[spawn_robot],
                            ),
                        ],
                    ),
                    event_spawn_robot,
                ]
            )
        else:
            # laser存在命名空间覆盖问题
            event_generate_last_action = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=last_action,
                    on_exit=[
                        TimerAction(
                            period=delay_between_robots,  # 4.0
                            actions=[
                                group_action_spawn_param,
                                TimerAction(
                                    period=delay_spawn_robot,  # 1.0
                                    actions=[spawn_robot],
                                ),
                            ],
                        ),
                    ],
                )
            )
            event_spawn_robot = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=spawn_robot,
                    on_exit=[
                        TimerAction(
                            period=delay_laser_tools,  # 3.0
                            actions=append_nodes,
                        ),
                    ],
                )
            )

            actions.extend(
                [
                    event_generate_last_action,
                    event_spawn_robot,
                ]
            )

        last_action = spawn_robot

    return actions


def generate_launch_description():
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
