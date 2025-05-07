import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from tf2_msgs.msg import TFMessage
from rclpy.time import Time


class RawTfToPosePublisher(Node):
    def __init__(self):
        super().__init__("raw_tf_to_pose_publisher")
        self.namespace = self.get_namespace()

        self.declare_parameter("sub_global_frame_id", "warehouse")
        self.declare_parameter("sub_base_link", f"{self.namespace}/robot")

        self.sub_global_frame_id = (
            self.get_parameter("sub_global_frame_id").get_parameter_value().string_value
        )
        self.sub_base_link = (
            self.get_parameter("sub_base_link").get_parameter_value().string_value
        )

        self.tf_sub = self.create_subscription(TFMessage, "/tf", self.tf_callback, 10)

        self.pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, "amcl_pose_tf", 10
        )

    def tf_callback(self, msg: TFMessage):
        for transform in msg.transforms:
            parent = transform.header.frame_id.strip("/")
            child = transform.child_frame_id.strip("/")

            if parent == self.sub_global_frame_id.strip(
                "/"
            ) and child == self.sub_base_link.strip("/"):
                pose_msg = PoseWithCovarianceStamped()
                pose_msg.header.stamp = transform.header.stamp
                pose_msg.header.frame_id = "map"

                pose_msg.pose.pose.position.x = transform.transform.translation.x
                pose_msg.pose.pose.position.y = transform.transform.translation.y
                pose_msg.pose.pose.position.z = transform.transform.translation.z

                pose_msg.pose.pose.orientation.x = transform.transform.rotation.x
                pose_msg.pose.pose.orientation.y = transform.transform.rotation.y
                pose_msg.pose.pose.orientation.z = transform.transform.rotation.z
                pose_msg.pose.pose.orientation.w = transform.transform.rotation.w

                self.pose_pub.publish(pose_msg)
                self.get_logger().debug(f"Published pose from {parent} -> {child}")
                break


def main(args=None):
    rclpy.init(args=args)
    node = RawTfToPosePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
