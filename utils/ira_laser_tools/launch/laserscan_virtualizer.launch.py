from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    tf_node_1 = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name='ira_static_broadcaster1',
        arguments=['0', '0', '0', '0.3', '0', '0', 'base_link', 'scansx'],
    )

    tf_node_2 = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name='ira_static_broadcaster2',
        arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'scandx'],
    )

    laserscan_virtualizer = Node(
        package='ira_laser_tools',
        namespace='',
        executable='laserscan_virtualizer',
        name='laserscan_virtualizer',
        output='screen',
        parameters=[{
            # INPUT POINT CLOUD
            "cloud_topic": "/trunk4_camera_depth_camera/points",
            # REFERENCE FRAME WHICH LASER(s) ARE RELATED
            "base_frame": "base_link",
            # VIRTUAL LASER OUTPUT TOPIC, LEAVE VALUE EMPTY TO PUBLISH ON THE VIRTUAL LASER NAMES (param: output_laser_scan)
            "output_laser_topic": "/scan",
            # LIST OF THE VIRTUAL LASER SCANS. YOU MUST PROVIDE THE STATIC TRANSFORMS TO TF, SEE ABOVE
            "virtual_laser_scan": "scansx scandx",
            'angle_min': -3.14,
            'angle_max': 3.14,
            'angle_increment': 0.00437,
            'scan_time': 0.0,
            'range_min': 0.1,
            'range_max': 2.0,
        }],
    )

    description = LaunchDescription()
    description.add_action(tf_node_1)
    description.add_action(tf_node_2)
    description.add_action(laserscan_virtualizer)
    return description
