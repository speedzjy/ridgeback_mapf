import rclpy
from rclpy.node import Node
import tf2_ros
import tf2_geometry_msgs
import yaml
from geometry_msgs.msg import TransformStamped


class TransformListenerNode(Node):
    def __init__(self):
        super().__init__("save_pose_node")

        # 获取当前节点的namespace
        self.namespace = self.get_namespace().strip("/")

        # 声明并获取参数
        self.declare_parameter(
            "global_frame_id", "warehouse"
        )  # 新增 global_frame_id 参数
        self.declare_parameter(
            "output_path", "/home/speed/clearpath/{namespace}/current_pose.yaml"
        )

        self.global_frame_id = (
            self.get_parameter("global_frame_id").get_parameter_value().string_value
        )
        self.output_path = (
            self.get_parameter("output_path").get_parameter_value().string_value
        )
        self.output_path = self.output_path.format(namespace=self.namespace)

        # 创建 tf2 的 buffer 和 listener
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 启动定时器，每隔 1 秒检查变换
        self.timer = self.create_timer(0.5, self.timer_callback)

    def timer_callback(self):
        try:
            # 监听变换：从 {namespace}/robot 到 global_frame_id
            transform = self.tf_buffer.lookup_transform(
                self.global_frame_id, f"{self.namespace}/robot", rclpy.time.Time()
            )
            # self.get_logger().info(
            #     f"Transform from {self.global_frame_id} to {self.namespace}/robot found."
            # )

            # 将变换保存为字典
            transform_data = {
                "translation": {
                    "x": transform.transform.translation.x,
                    "y": transform.transform.translation.y,
                    "z": transform.transform.translation.z,
                },
                "rotation": {
                    "x": transform.transform.rotation.x,
                    "y": transform.transform.rotation.y,
                    "z": transform.transform.rotation.z,
                    "w": transform.transform.rotation.w,
                },
            }

            # 将数据保存到 YAML 文件
            with open(self.output_path, "w") as yaml_file:
                yaml.dump(transform_data, yaml_file)
            # self.get_logger().info(f"Transform saved to {self.output_path}")

        except tf2_ros.TransformException as e:
            self.get_logger().warn(f"Could not get transform: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = TransformListenerNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
