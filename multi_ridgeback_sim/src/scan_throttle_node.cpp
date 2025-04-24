#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>

using std::placeholders::_1;

class ScanThrottle : public rclcpp::Node
{
public:
  ScanThrottle()
  : Node("scan_throttle")
  {
    input_topic_ = this->declare_parameter<std::string>("input_topic", "scan_full");
    output_topic_ = this->declare_parameter<std::string>("output_topic", "scan_full_throttled");
    rate_ = this->declare_parameter<double>("rate", 10.0);  // Hz

    auto qos = rclcpp::SensorDataQoS();

    publisher_ = this->create_publisher<sensor_msgs::msg::LaserScan>(output_topic_, qos);
    subscription_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
      input_topic_, qos, std::bind(&ScanThrottle::scan_callback, this, _1));

    timer_ = this->create_wall_timer(
      std::chrono::duration<double>(1.0 / rate_),
      std::bind(&ScanThrottle::timer_callback, this));
  }

private:
  void scan_callback(const sensor_msgs::msg::LaserScan::SharedPtr msg)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    latest_msg_ = msg;
  }

  void timer_callback()
  {
    std::lock_guard<std::mutex> lock(mutex_);
    if (latest_msg_) {
      publisher_->publish(*latest_msg_);
      latest_msg_.reset();
    }
  }

  std::string input_topic_;
  std::string output_topic_;
  double rate_;

  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr publisher_;
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timer_;
  sensor_msgs::msg::LaserScan::SharedPtr latest_msg_;
  std::mutex mutex_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ScanThrottle>());
  rclcpp::shutdown();
  return 0;
}
