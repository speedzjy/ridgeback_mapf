# Copyright 2019 Open Source Robotics Foundation, Inc.
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
# Author: Darby Lim

import os

from ament_index_python.packages import get_package_share_directory

from clearpath_config.common.utils.yaml import read_yaml
from clearpath_config.clearpath_config import ClearpathConfig

from launch import LaunchDescription

from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)

from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    EnvironmentVariable,
    PathJoinSubstitution,
)
from launch.substitutions import ThisLaunchFileDir
from launch_ros.actions import Node, PushRosNamespace, SetRemap


ARGUMENTS = [
    DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        choices=["true", "false"],
        description="Use sim time",
    ),
    DeclareLaunchArgument(
        "setup_path",
        default_value=[EnvironmentVariable("HOME"), "/clearpath/rb_0/"],
        description="Clearpath setup path",
    ),
]


def launch_setup(context, *args, **kwargs):
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    setup_path = LaunchConfiguration("setup_path")
    config = read_yaml(setup_path.perform(context) + "robot.yaml")
    clearpath_config = ClearpathConfig(config)
    namespace = clearpath_config.system.namespace

    pkg_clearpath_nav2_demos = get_package_share_directory("multi_ridgeback_sim")
    pkg_nav2_bringup = get_package_share_directory("nav2_bringup")
    
    cartographer_config_dir = LaunchConfiguration(
        "cartographer_config_dir",
        default=os.path.join(pkg_clearpath_nav2_demos, "config"),
    )
    configuration_basename = LaunchConfiguration(
        "configuration_basename", default="carto_map.lua"
    )

    resolution = LaunchConfiguration("resolution", default="0.05")
    publish_period_sec = LaunchConfiguration("publish_period_sec", default="1.0")

    rviz_config_dir = os.path.join(
        get_package_share_directory("multi_ridgeback_sim"), "rviz", "slam.rviz"
    )

    carto = GroupAction(
        [
            PushRosNamespace(namespace),
            DeclareLaunchArgument(
                "cartographer_config_dir",
                default_value=cartographer_config_dir,
                description="Full path to config file to load",
            ),
            DeclareLaunchArgument(
                "configuration_basename",
                default_value=configuration_basename,
                description="Name of lua file for cartographer",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value=use_sim_time,
                description="Use simulation (Gazebo) clock if true",
            ),
            Node(
                package="cartographer_ros",
                executable="cartographer_node",
                name="cartographer_node",
                output="screen",
                parameters=[{"use_sim_time": use_sim_time}],
                arguments=[
                    "-configuration_directory",
                    cartographer_config_dir,
                    "-configuration_basename",
                    configuration_basename,
                ],
                remappings=[
                    ("/tf", "tf"),
                    ("/tf_static", "tf_static"),
                    ("scan", "scan_full"),
                    ("map", "map"),
                ],
            ),
            DeclareLaunchArgument(
                "resolution",
                default_value=resolution,
                description="Resolution of a grid cell in the published occupancy grid",
            ),
            DeclareLaunchArgument(
                "publish_period_sec",
                default_value=publish_period_sec,
                description="OccupancyGrid publishing period",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [ThisLaunchFileDir(), "/occupancy_grid.launch.py"]
                ),
                launch_arguments={
                    "use_sim_time": use_sim_time,
                    "resolution": resolution,
                    "publish_period_sec": publish_period_sec,
                }.items(),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", rviz_config_dir],
                parameters=[{"use_sim_time": use_sim_time}],
                remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
                output="screen",
            ),
        ]
    )

    # nav
    nav2_parameters = PathJoinSubstitution(
        [pkg_clearpath_nav2_demos, "config", "nav2.yaml"]
    )
    launch_nav2 = PathJoinSubstitution(
        [pkg_nav2_bringup, "launch", "navigation_launch.py"]
    )
    nav2 = GroupAction(
        [
            PushRosNamespace(namespace),
            SetRemap(
                "/" + namespace + "/global_costmap/scan_full",
                "/" + namespace + "/scan_full",
            ),
            SetRemap(
                "/" + namespace + "/local_costmap/scan_full",
                "/" + namespace + "/scan_full",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_nav2),
                launch_arguments=[
                    ("use_sim_time", use_sim_time),
                    ("params_file", nav2_parameters),
                    ("use_composition", "False"),
                    ("namespace", namespace),
                ],
            ),
        ]
    )

    delayed_nav2 = TimerAction(period=4.0, actions=[nav2])
    
    actions = [carto, delayed_nav2]
    return actions


def generate_launch_description():
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
