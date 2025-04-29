import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped
import tf2_ros
import tf_transformations
import numpy as np


class AmclTfBroadcaster(Node):

    def __init__(self):
        super().__init__("amcl_tf_broadcaster")
        self.declare_parameter('use_sim_time', True)
        use_sim_time = self.get_parameter('use_sim_time').get_parameter_value().bool_value

        # 创建 TransformBroadcaster
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # 创建 tf2 Buffer 和 Listener，用来查找 odom->base_link
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 订阅 amcl_pose_tf
        self.subscription = self.create_subscription(
            PoseWithCovarianceStamped,
            "amcl_pose_tf",  # 如果话题名不同，请修改这里
            self.listener_callback,
            10,
        )

        self.get_logger().info("AMCL TF Broadcaster initialized")

    def listener_callback(self, msg: PoseWithCovarianceStamped):
        try:
            # 尝试查找 odom -> base_link 的实时变换
            trans = self.tf_buffer.lookup_transform(
                "odom",
                "base_link",
                self.get_clock().now().to_msg(),  # 最新
                timeout=rclpy.duration.Duration(seconds=0.5),
            )
        except (
            tf2_ros.LookupException,
            tf2_ros.ConnectivityException,
            tf2_ros.ExtrapolationException,
        ) as e:
            self.get_logger().warn(f"Could not get odom->base_link transform: {e}")
            return

        # 获取 amcl_pose 的 map->base_link 变换
        pose = msg.pose.pose

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
            trans.transform.translation.x,
            trans.transform.translation.y,
            trans.transform.translation.z,
            trans.transform.rotation.x,
            trans.transform.rotation.y,
            trans.transform.rotation.z,
            trans.transform.rotation.w,
        )

        # 计算 map -> odom = map->base_link * inverse(odom->base_link)
        base_to_odom = np.linalg.inv(odom_to_base)
        map_to_odom = np.matmul(map_to_base, base_to_odom)

        # 提取变换
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
        # 平移矩阵
        translation = tf_transformations.translation_matrix((x, y, z))
        # 旋转矩阵
        rotation = tf_transformations.quaternion_matrix((qx, qy, qz, qw))
        # 综合成一个4x4矩阵
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
