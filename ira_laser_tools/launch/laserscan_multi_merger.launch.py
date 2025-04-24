from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    GroupAction,
    TimerAction,
    RegisterEventHandler,
    LogInfo,
)
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
    TextSubstitution,
)

ARGUMENTS = [
    DeclareLaunchArgument("namespace", default_value="", description="Robot namespace")
]


def launch_setup(context, *args, **kwargs):
    namespace_value = LaunchConfiguration("namespace").perform(context)
    # print("Actual namespace:", namespace_value)

    laserscan_multi_merger = Node(
        package="ira_laser_tools",
        namespace=namespace_value,  # 这里传的是字符串
        executable="laserscan_multi_merger",
        name="laserscan_multi_merger",
        output="screen",
        remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
        parameters=[
            {
                "destination_frame": "lidar2d_0_laser",
                "cloud_destination_topic": "merged_cloud",
                "scan_destination_topic": "scan_full",
                "laserscan_topics": f"/{namespace_value}/sensors/lidar2d_0/scan /{namespace_value}/sensors/lidar2d_1/scan",
                "angle_min": -3.14,
                "angle_max": 3.14,
                "angle_increment": 0.003,
                "scan_time": 0.05,
                "range_min": 0.1,
                "range_max": 40.0,
            }
        ],
    )

    return [laserscan_multi_merger]


def generate_launch_description():
    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(OpaqueFunction(function=launch_setup))
    return ld
