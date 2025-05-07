import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import json
import os
import threading
import time
from tf_transformations import euler_from_quaternion
from ament_index_python.packages import get_package_share_directory

package_path = get_package_share_directory("task_communication")


class PoseRecorder(Node):
    def __init__(self):
        super().__init__("pose_recorder")
        self.declare_parameter("station_json", "station.json")
        self.pose_sub = self.create_subscription(
            PoseWithCovarianceStamped, "amcl_pose_tf", self.pose_callback, 10
        )
        self.cur_pose = None
        self.record_thread = threading.Thread(target=self.record_loop)
        self.record_thread.daemon = True
        self.record_thread.start()

    def pose_callback(self, msg):
        self.cur_pose = msg

    def is_file_exist(self, path):
        return os.path.isfile(path)

    def record_loop(self):
        while rclpy.ok():
            print("记录机器人位姿输入1，退出输入0: ")
            try:
                record = int(input())
                if record == 0:
                    break
                if record != 1:
                    continue

                if self.cur_pose is None:
                    print("当前位姿为空，等待接收 amcl_pose_tf 消息...")
                    time.sleep(1)
                    continue

                station_name = input("输入站点名称: ").strip()

                pose_msg = self.cur_pose.pose.pose
                position = {
                    "x": pose_msg.position.x,
                    "y": pose_msg.position.y,
                    "z": pose_msg.orientation.z,
                    "w": pose_msg.orientation.w,
                }

                station_position = {station_name: position}

                json_path = (
                    self.get_parameter("station_json")
                    .get_parameter_value()
                    .string_value
                )
                json_path = f"{package_path}/station_cfg/{json_path}"
                if not self.is_file_exist(json_path):
                    with open(json_path, "w") as f:
                        f.write("{}")
                        print(f"创建新文件 {json_path}")

                with open(json_path, "r") as f:
                    try:
                        root = json.load(f)
                    except json.JSONDecodeError:
                        root = {}

                root.update(station_position)
                print("更新站点数据...")

                with open(json_path, "w") as f:
                    json.dump(root, f, indent=2)

                _, _, yaw = euler_from_quaternion(
                    [
                        pose_msg.orientation.x,
                        pose_msg.orientation.y,
                        pose_msg.orientation.z,
                        pose_msg.orientation.w,
                    ]
                )

                print(
                    f"记录: \nname: {station_name}\npose:\nx: {pose_msg.position.x:.3f}\n"
                    f"y: {pose_msg.position.y:.3f}\nyaw: {yaw:.3f}"
                )
                print("记录完毕! 去下一个站点.\n")

            except Exception as e:
                print(f"输入或处理出错: {e}")
                time.sleep(1)


def main(args=None):
    rclpy.init(args=args)
    node = PoseRecorder()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
