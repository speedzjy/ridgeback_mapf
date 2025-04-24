#include <memory>
#include <string>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2_msgs/msg/tf_message.hpp"

class TfNamespaceRelay : public rclcpp::Node {
public:
  TfNamespaceRelay() : Node("tf_namespace_relay") {
    prefix_ = this->get_namespace();
    // tf 和 tf_static 输入话题
    std::string tf_in = "tf";
    std::string tf_static_in = "tf_static";

    tf_sub_ = this->create_subscription<tf2_msgs::msg::TFMessage>(
        tf_in, 10,
        std::bind(&TfNamespaceRelay::tf_callback, this, std::placeholders::_1));

    rclcpp::QoS qos_transient =
        rclcpp::QoS(rclcpp::KeepLast(10)).transient_local();

    tf_static_sub_ = this->create_subscription<tf2_msgs::msg::TFMessage>(
        tf_static_in, qos_transient,
        std::bind(&TfNamespaceRelay::tf_static_callback, this,
                  std::placeholders::_1));

    tf_pub_ = this->create_publisher<tf2_msgs::msg::TFMessage>("/tf", 10);
    tf_static_pub_ = this->create_publisher<tf2_msgs::msg::TFMessage>(
        "/tf_static", rclcpp::QoS(rclcpp::KeepLast(10)).transient_local());

    // 添加 map -> prefix_/map 的静态变换
    tf2_msgs::msg::TFMessage static_msg;
    geometry_msgs::msg::TransformStamped transform;
    transform.header.stamp = this->now();
    transform.header.frame_id = "/map";
    transform.child_frame_id = prefix_ + "/map";
    transform.transform.translation.x = 0.0;
    transform.transform.translation.y = 0.0;
    transform.transform.translation.z = 0.0;
    transform.transform.rotation.x = 0.0;
    transform.transform.rotation.y = 0.0;
    transform.transform.rotation.z = 0.0;
    transform.transform.rotation.w = 1.0;
    static_msg.transforms.push_back(transform);
    tf_static_pub_->publish(static_msg);
  }

private:
  void tf_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg) {
    auto new_msg = process_message(msg);
    tf_pub_->publish(new_msg);
  }

  void tf_static_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg) {
    auto new_msg = process_message(msg);
    tf_static_pub_->publish(new_msg);
  }

  tf2_msgs::msg::TFMessage
  process_message(const tf2_msgs::msg::TFMessage::SharedPtr &msg) {
    tf2_msgs::msg::TFMessage new_msg;
    for (const auto &t : msg->transforms) {
      auto t_copy = t;
      t_copy.header.frame_id = prefix_if_needed(t.header.frame_id);
      t_copy.child_frame_id = prefix_if_needed(t.child_frame_id);
      new_msg.transforms.push_back(t_copy);
    }
    return new_msg;
  }

  std::string prefix_if_needed(const std::string &frame) {
    if (frame.rfind(prefix_, 0) == 0)
      return frame;
    return prefix_ + "/" + frame;
  }

  std::string prefix_;
  rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr tf_sub_;
  rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr tf_static_sub_;
  rclcpp::Publisher<tf2_msgs::msg::TFMessage>::SharedPtr tf_pub_;
  rclcpp::Publisher<tf2_msgs::msg::TFMessage>::SharedPtr tf_static_pub_;
};

int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TfNamespaceRelay>());
  rclcpp::shutdown();
  return 0;
}
