import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.duration import Duration

from rclpy.task import Future
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped


class NavigateToPoseClient(Node):
    def __init__(self):
        super().__init__('navigate_to_pose_client')
        self._action_client = ActionClient(self, NavigateToPose, '/rb_0/navigate_to_pose')
        self._goal_handle = None

    def send_goal(self, pose):
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = pose['x']
        goal_msg.pose.pose.position.y = pose['y']
        goal_msg.pose.pose.position.z = pose['z']
        goal_msg.pose.pose.orientation.x = pose['qx']
        goal_msg.pose.pose.orientation.y = pose['qy']
        goal_msg.pose.pose.orientation.z = pose['qz']
        goal_msg.pose.pose.orientation.w = pose['qw']

        goal_msg.behavior_tree = ''

        self._action_client.wait_for_server()
        self.get_logger().info(f'Sending goal to position: {pose}')
        self._send_goal_future = self._action_client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future: Future):
        self._goal_handle = future.result()
        if not self._goal_handle.accepted:
            self.get_logger().info('Goal rejected :(')
            return

        self.get_logger().info('Goal accepted :)')

        self._get_result_future = self._goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future: Future):
        result = future.result()
        


def main(args=None):
    rclpy.init(args=args)
    node = NavigateToPoseClient()

    # 定义三个目标点
    targets = [
        {'x': 0.0, 'y': -2.0, 'z': 0.0, 'qx': 0.0, 'qy': 0.0, 'qz': 0.0, 'qw': 1.0},
        # {'x': 2.0, 'y': 1.0, 'z': 0.0, 'qx': 0.0, 'qy': 0.0, 'qz': 0.0, 'qw': 1.0},
        # {'x': 0.0, 'y': 5.0, 'z': 0.0, 'qx': 0.0, 'qy': 0.0, 'qz': 0.0, 'qw': 1.0}
    ]

    # 连续发送目标点
    for target in targets:
        node.send_goal(target)
        rclpy.spin_once(node)  # 确保目标发送完成
        node.get_clock().sleep_for(Duration(seconds=5))  # 间隔一秒发送下一个目标
        rclpy.spin_once(node)

    rclpy.spin(node)  # 保持节点运行直到收到所有结果
    rclpy.shutdown()


if __name__ == '__main__':
    main()
