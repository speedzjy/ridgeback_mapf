#include <iostream>
#include <string>
#include <vector>

#include <ros/ros.h>

#include <geometry_msgs/TransformStamped.h>
#include <nav_msgs/Odometry.h>
#include <sensor_msgs/Imu.h>
#include <sensor_msgs/LaserScan.h>

#include <mutex>
#include <thread>

using namespace std;

class TransLaserFrame {
public:
  ros::NodeHandle nh;
  ros::Subscriber subFrontLaser;
  ros::Publisher pubFrontLaser;
  ros::Subscriber subRearLaser;
  ros::Publisher pubRearLaser;

  string tf_prefix;

public:
  TransLaserFrame() {
    nh.param<std::string>("laser_frame_correct/tf_prefix", tf_prefix, "rb_0");
    subFrontLaser = nh.subscribe("front/scan", 1, &TransLaserFrame::frontLaserCallback, this);
    pubFrontLaser = nh.advertise<sensor_msgs::LaserScan>("front/scan_correct", 1);
    subRearLaser = nh.subscribe("rear/scan", 1, &TransLaserFrame::rearLaserCallback, this);
    pubRearLaser = nh.advertise<sensor_msgs::LaserScan>("rear/scan_correct", 1);
  }
  ~TransLaserFrame() {}

  void frontLaserCallback(const sensor_msgs::LaserScanConstPtr &scan) {
    sensor_msgs::LaserScan this_scan = *scan;
    this_scan.header.frame_id = tf_prefix + "/" + "front_laser";
    pubFrontLaser.publish(this_scan);
  }

  void rearLaserCallback(const sensor_msgs::LaserScanConstPtr &scan) {
    sensor_msgs::LaserScan this_scan = *scan;
    this_scan.header.frame_id = tf_prefix + "/" + "rear_laser";
    pubRearLaser.publish(this_scan);
  }

};

int main(int argc, char **argv) {
  ros::init(argc, argv, "laser_frame_correct");

  TransLaserFrame TOIF;

  ROS_INFO("\033[1;32m----> Started TransLaserFrame with tf_prefix.\033[0m");

  ros::MultiThreadedSpinner spinner(1);
  spinner.spin();

  return 0;
}