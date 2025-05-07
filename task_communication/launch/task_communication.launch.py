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
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

ARGUMENTS = [
    DeclareLaunchArgument(
        "station_pose_path",
        default_value=[
            PathJoinSubstitution(
                [FindPackageShare("task_communication"), "station_cfg", "station.json"]
            )
        ],
        description="Path to the station pose file",
    ),
    DeclareLaunchArgument(
        "namespace",
        default_value="rb_0",
        description="Path to the station pose file",
    ),
]


def launch_setup(context, *args, **kwargs):
    station_pose_path = LaunchConfiguration("station_pose_path")
    namespace = LaunchConfiguration("namespace")

    return [
        Node(
            namespace=namespace.perform(context),
            package="task_communication",
            executable="platform_communication",
            name="platform_communication_node",
            output="screen",
            parameters=[],
            arguments=["--path", station_pose_path],
        ),
    ]


def generate_launch_description():
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
