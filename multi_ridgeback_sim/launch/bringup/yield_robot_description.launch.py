# Copyright 2021 Clearpath Robotics, Inc.
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

from clearpath_config.clearpath_config import ClearpathConfig
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    RegisterEventHandler,
    OpaqueFunction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
)

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

import os


ARGUMENTS = [
    DeclareLaunchArgument(
        "yield_setup_path",
        default_value=[EnvironmentVariable("HOME"), "/clearpath/"],
        description="Clearpath setup path",
    ),
]

ROBOT_LIST = [f"rb_{i}" for i in range(0, 5)]


def launch_setup(context, *args, **kwargs):
    yield_setup_path = LaunchConfiguration("yield_setup_path")

    last_action = None
    actions = []
    for robot_index, robot in enumerate(ROBOT_LIST):
        single_robot_path = PathJoinSubstitution([yield_setup_path, robot])
        print("Setup path: ", str(yield_setup_path.perform(context)))
        print(os.path.join(str(single_robot_path.perform(context))))

        # Parse robot YAML into config
        clearpath_config = ClearpathConfig(
            os.path.join(str(single_robot_path.perform(context)), "robot.yaml")
        )
        namespace = clearpath_config.system.namespace
        robot_name = "robot" if namespace in ("", "/") else namespace + "/robot"

        node_generate_description = Node(
            package="clearpath_generator_common",
            executable="generate_description",
            name="generate_description",
            output="screen",
            arguments=["-s", single_robot_path],
        )

        node_generate_semantic_description = Node(
            package="clearpath_generator_common",
            executable="generate_semantic_description",
            name="generate_semantic_description",
            output="screen",
            arguments=["-s", single_robot_path],
        )

        node_generate_launch = Node(
            package="clearpath_generator_gz",
            executable="generate_launch",
            name="generate_launch",
            output="screen",
            arguments=["-s", single_robot_path],
        )

        node_generate_param = Node(
            package="clearpath_generator_gz",
            executable="generate_param",
            name="generate_launch",
            output="screen",
            arguments=["-s", single_robot_path],
        )

        if robot_index == 0:
            event_generate_description = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=node_generate_description,
                    on_exit=[node_generate_semantic_description],
                )
            )

            event_generate_semantic_description = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=node_generate_semantic_description,
                    on_exit=[node_generate_launch],
                )
            )

            event_generate_launch = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=node_generate_launch, on_exit=[node_generate_param]
                )
            )

            actions.extend(
                [
                    node_generate_description,
                    event_generate_description,
                    event_generate_semantic_description,
                    event_generate_launch,
                ]
            )
        else:
            event_generate_last_action = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=last_action,  # Wait for the last robot's last action
                    on_exit=[node_generate_description],
                )
            )

            event_generate_description = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=node_generate_description,
                    on_exit=[node_generate_semantic_description],
                )
            )

            event_generate_semantic_description = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=node_generate_semantic_description,
                    on_exit=[node_generate_launch],
                )
            )

            event_generate_launch = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=node_generate_launch, on_exit=[node_generate_param]
                )
            )

            actions.extend(
                [
                    event_generate_last_action,
                    event_generate_description,
                    event_generate_semantic_description,
                    event_generate_launch,
                ]
            )

        last_action = node_generate_param

    return actions


def generate_launch_description():
    # Define LaunchDescription variable
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
