#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"

class ScanFrameRelay : public rclcpp::Node {
public:
  ScanFrameRelay()
    : Node("scan_frame_relay") {

    // 获取命名空间（去掉开头的 /）
    std::string ns = this->get_namespace();
    if (!ns.empty() && ns.front() == '/') {
      ns.erase(0, 1);
    }
    namespace_ = ns;

    // 使用 SensorDataQoS 订阅原始 scan
    scan_sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
      "scan_full", rclcpp::SensorDataQoS(),
      std::bind(&ScanFrameRelay::scan_callback, this, std::placeholders::_1));

    // 使用 SensorDataQoS 发布修改后的 scan
    scan_pub_ = this->create_publisher<sensor_msgs::msg::LaserScan>(
      "scan_full_prefix", rclcpp::SensorDataQoS());
  }

private:
  void scan_callback(sensor_msgs::msg::LaserScan::SharedPtr msg) {
    auto base_frame = msg->header.frame_id;
    auto new_msg = *msg;
    new_msg.header.frame_id = namespace_ + "/" + base_frame;
    scan_pub_->publish(new_msg);
  }

  std::string namespace_;
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr scan_pub_;
};

int main(int argc, char * argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ScanFrameRelay>());
  rclcpp::shutdown();
  return 0;
}
