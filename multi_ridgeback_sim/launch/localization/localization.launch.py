# Software License Agreement (BSD)
#
# @author    Roni Kreinin <rkreinin@clearpathrobotics.com>
# @copyright (c) 2023, Clearpath Robotics, Inc., All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of Clearpath Robotics nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
from ament_index_python.packages import get_package_share_directory

from clearpath_config.common.utils.yaml import read_yaml
from clearpath_config.clearpath_config import ClearpathConfig

from launch import LaunchDescription
from launch.conditions import IfCondition

from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    EnvironmentVariable,
)

from launch_ros.actions import Node, PushRosNamespace, SetRemap

from launch_ros.descriptions import ComposableNode, ParameterFile
from nav2_common.launch import RewrittenYaml


ARGUMENTS = [
    DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        choices=["true", "false"],
        description="Use sim time",
    ),
    DeclareLaunchArgument(
        "namespace",
        default_value=["rb_0"],
        description="Clearpath namespace",
    ),
    DeclareLaunchArgument(
        "use_rviz",
        default_value=["false"],
        choices=["true", "false"],
        description="Use rviz",
    ),
]


def launch_setup(context, *args, **kwargs):
    # Packages
    # pkg_clearpath_nav2_demos = get_package_share_directory('clearpath_nav2_demos')
    pkg_clearpath_nav2_demos = get_package_share_directory("multi_ridgeback_sim")
    # pkg_nav2_bringup = get_package_share_directory("nav2_bringup")
    pkg_nav2_bringup = get_package_share_directory("multi_ridgeback_sim")

    # Launch Configurations
    use_sim_time = LaunchConfiguration("use_sim_time")
    map_file = LaunchConfiguration("map")

    namespace = str(LaunchConfiguration("namespace").perform(context))

    file_parameters = PathJoinSubstitution(
        [pkg_clearpath_nav2_demos, "config", "localization.yaml"]
    )

    launch_localization = PathJoinSubstitution(
        [pkg_nav2_bringup, "launch/include", "localization_launch.py"]
    )

    localization = GroupAction(
        [
            PushRosNamespace(namespace),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_localization),
                launch_arguments=[
                    ("namespace", namespace),
                    ("map", map_file),
                    ("use_sim_time", use_sim_time),
                    ("params_file", file_parameters),
                ],
            ),
        ]
    )

    # nav
    nav2_parameters = PathJoinSubstitution(
        [pkg_clearpath_nav2_demos, "config", "nav2.yaml"]
    )
    launch_nav2 = PathJoinSubstitution(
        [pkg_nav2_bringup, "launch/include", "navigation_launch.py"]
    )
    nav2 = GroupAction(
        [
            PushRosNamespace(namespace),
            SetRemap(
                "global_costmap/scan_full",
                "scan_full",
            ),
            SetRemap(
                "local_costmap/scan_full",
                "scan_full",
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

    actions = [
        TimerAction(
            period=0.0,
            actions=[
                localization,
                TimerAction(period=1.0, actions=[nav2]),
            ],
        ),
    ]

    return actions


def generate_launch_description():
    pkg_clearpath_nav2_demos = get_package_share_directory("clearpath_nav2_demos")

    map_arg = DeclareLaunchArgument(
        "map",
        default_value=PathJoinSubstitution(
            [pkg_clearpath_nav2_demos, "maps", "warehouse.yaml"]
        ),
        description="Full path to map yaml file to load",
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(map_arg)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
