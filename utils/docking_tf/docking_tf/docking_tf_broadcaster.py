import time
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped
import tf2_ros
import tf_transformations
import numpy as np
from tf2_msgs.msg import TFMessage


class AmclTfBroadcaster(Node):

    def __init__(self):
        super().__init__("amcl_tf_broadcaster")
        self.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, True)])

        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        self.subscription = self.create_subscription(
            PoseWithCovarianceStamped,
            "amcl_pose_tf",
            self.amcl_pose_callback,
            10,
        )

        self.create_subscription(
            TFMessage,
            "/tf",
            self.tf_callback,
            50,
        )

        self.latest_odom_to_base = None
        self.latest_amcl_pose = None

        self.timer = self.create_timer(0.2, self.publish_transform)

        self.get_logger().info("AMCL TF Broadcaster initialized")

    def tf_callback(self, msg: TFMessage):
        for transform in msg.transforms:
            parent = transform.header.frame_id.strip("/")
            child = transform.child_frame_id.strip("/")

            if parent == "odom" and child == "base_link":
                self.latest_odom_to_base = transform
                break

    def amcl_pose_callback(self, msg: PoseWithCovarianceStamped):
        self.latest_amcl_pose = msg

    def publish_transform(self):
        if self.latest_amcl_pose is None or self.latest_odom_to_base is None:
            return

        # 获取 amcl_pose 的 map->base_link 变换
        pose = self.latest_amcl_pose.pose.pose

        # 将 map->base_link 转成 4x4矩阵
        map_to_base = self.transform_to_matrix(
            pose.position.x,
            pose.position.y,
            pose.position.z,
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        )

        # 将 odom->base_link 转成 4x4矩阵
        odom_to_base = self.transform_to_matrix(
            self.latest_odom_to_base.transform.translation.x,
            self.latest_odom_to_base.transform.translation.y,
            self.latest_odom_to_base.transform.translation.z,
            self.latest_odom_to_base.transform.rotation.x,
            self.latest_odom_to_base.transform.rotation.y,
            self.latest_odom_to_base.transform.rotation.z,
            self.latest_odom_to_base.transform.rotation.w,
        )

        # 计算 map -> odom = map->base_link * inverse(odom->base_link)
        try:
            base_to_odom = tf_transformations.inverse_matrix(odom_to_base)
        except np.linalg.LinAlgError as e:
            self.get_logger().warn(f"Matrix inversion failed: {e}")
            return

        map_to_odom = np.matmul(map_to_base, base_to_odom)
        translation = map_to_odom[:3, 3]
        rotation = tf_transformations.quaternion_from_matrix(map_to_odom)

        # 发布 map->odom
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "map"
        t.child_frame_id = "odom"
        t.transform.translation.x = translation[0]
        t.transform.translation.y = translation[1]
        t.transform.translation.z = translation[2]
        t.transform.rotation.x = rotation[0]
        t.transform.rotation.y = rotation[1]
        t.transform.rotation.z = rotation[2]
        t.transform.rotation.w = rotation[3]

        self.tf_broadcaster.sendTransform(t)
        self.get_logger().debug("Published map -> odom transform")

    @staticmethod
    def transform_to_matrix(x, y, z, qx, qy, qz, qw):
        translation = tf_transformations.translation_matrix((x, y, z))
        rotation = tf_transformations.quaternion_matrix((qx, qy, qz, qw))
        return np.matmul(translation, rotation)


def main(args=None):
    rclpy.init(args=args)
    node = AmclTfBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
