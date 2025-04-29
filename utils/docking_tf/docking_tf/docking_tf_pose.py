import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseWithCovarianceStamped
import rclpy.time
import rclpy.timer
import tf2_ros
from tf2_ros import TransformException


class AmclPoseTfPublisher(Node):
    def __init__(self):
        super().__init__("amcl_pose_tf_publisher")
        self.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, True)])

        # 声明参数
        self.declare_parameter("sub_global_frame_id", "warehouse")
        self.declare_parameter("sub_base_link", "rb_0/robot")

        self.sub_global_frame_id = (
            self.get_parameter("sub_global_frame_id").get_parameter_value().string_value
        )
        self.sub_base_link = (
            self.get_parameter("sub_base_link").get_parameter_value().string_value
        )

        # TF Buffer 和 Listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 发布器
        self.pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, "amcl_pose_tf", 5
        )

        # 定时器，10Hz频率查询
        self.timer = self.create_timer(0.02, self.timer_callback)

    def timer_callback(self):
        try:
            trans = self.tf_buffer.lookup_transform(
                self.sub_global_frame_id,
                self.sub_base_link,
                # self.get_clock().now().to_msg(),
                timeout=rclpy.duration.Duration(seconds=0.2),
            )

            pose_msg = PoseWithCovarianceStamped()
            pose_msg.header.stamp = trans.header.stamp
            pose_msg.header.frame_id = "map"

            # 填充位置
            pose_msg.pose.pose.position.x = trans.transform.translation.x
            pose_msg.pose.pose.position.y = trans.transform.translation.y
            pose_msg.pose.pose.position.z = trans.transform.translation.z

            # 填充姿态
            pose_msg.pose.pose.orientation = trans.transform.rotation

            self.pose_pub.publish(pose_msg)

        except TransformException as ex:
            self.get_logger().warn(
                f"Cannot transform {self.sub_global_frame_id} -> {self.sub_base_link}: {ex}"
            )


def main(args=None):
    rclpy.init(args=args)
    node = AmclPoseTfPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
