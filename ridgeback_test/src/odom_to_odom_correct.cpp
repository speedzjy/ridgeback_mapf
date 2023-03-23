#include <iostream>
#include <string>
#include <vector>

#include <ros/ros.h>

#include <geometry_msgs/TransformStamped.h>
#include <nav_msgs/Odometry.h>
#include <sensor_msgs/Imu.h>

#include <mutex>
#include <thread>

using namespace std;

class TransOdomImuFrame {
public:
  ros::NodeHandle nh;
  ros::Subscriber subOdom;
  ros::Subscriber subControllerOdom;
  ros::Subscriber subImu;
  ros::Publisher pubOdom;
  ros::Publisher pubControllerOdom;
  ros::Publisher pubImu;

  string tf_prefix;

public:
  TransOdomImuFrame() {
    nh.param<std::string>("odom_to_odom_correct/tf_prefix", tf_prefix, "rb_0");

    subOdom = nh.subscribe("odom", 1, &TransOdomImuFrame::odomCallback, this);
    subControllerOdom =
        nh.subscribe("ridgeback_velocity_controller/odom", 1,
                     &TransOdomImuFrame::ControllerOdomCallback, this);
    subImu = nh.subscribe("imu/data", 1, &TransOdomImuFrame::imuCallback, this);

    pubOdom = nh.advertise<nav_msgs::Odometry>("odom_correct", 1);
    pubControllerOdom = nh.advertise<nav_msgs::Odometry>(
        "ridgeback_velocity_controller/odom_correct", 1);
    pubImu = nh.advertise<sensor_msgs::Imu>("imu/data_correct", 1);
  }
  ~TransOdomImuFrame() {}

  void odomCallback(const nav_msgs::OdometryConstPtr &odom) {
    nav_msgs::Odometry this_odom = *odom;
    this_odom.header.frame_id = tf_prefix + "/" + odom->header.frame_id;
    this_odom.child_frame_id = tf_prefix + "/" + odom->child_frame_id;
    pubOdom.publish(this_odom);
  }

  void
  ControllerOdomCallback(const nav_msgs::OdometryConstPtr &controllerOdom) {
    nav_msgs::Odometry this_odom = *controllerOdom;
    this_odom.header.frame_id =
        tf_prefix + "/" + controllerOdom->header.frame_id;
    this_odom.child_frame_id = tf_prefix + "/" + controllerOdom->child_frame_id;
    pubControllerOdom.publish(this_odom);
  }

  void imuCallback(const sensor_msgs::ImuConstPtr &imu) {
    sensor_msgs::Imu this_imu = *imu;
    this_imu.header.frame_id = tf_prefix + "/" + imu->header.frame_id;
    pubImu.publish(this_imu);
  }
};

int main(int argc, char **argv) {
  ros::init(argc, argv, "odom_to_odom_correct");

  TransOdomImuFrame TOIF;

  ROS_INFO("\033[1;32m----> Started TransOdomImuFrame with tf_prefix.\033[0m");

  ros::MultiThreadedSpinner spinner(3);
  spinner.spin();

  return 0;
}