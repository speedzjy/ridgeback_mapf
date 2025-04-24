cmake_minimum_required(VERSION 3.8)
project(multi_ridgeback_sim)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(rclcpp REQUIRED)
find_package(tf2_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# node
add_executable(tf_namespace_relay src/tf_namespace_relay.cpp)
ament_target_dependencies(tf_namespace_relay rclcpp tf2_msgs)
install(TARGETS
  tf_namespace_relay
  DESTINATION lib/${PROJECT_NAME}
)

add_executable(scan_throttle_node src/scan_throttle_node.cpp)
ament_target_dependencies(scan_throttle_node rclcpp sensor_msgs)
install(TARGETS scan_throttle_node DESTINATION lib/${PROJECT_NAME})

add_executable(scan_frame_relay src/scan_frame_relay.cpp)
ament_target_dependencies(scan_frame_relay rclcpp sensor_msgs)
install(TARGETS scan_frame_relay DESTINATION lib/${PROJECT_NAME})


# others
install(
  DIRECTORY config launch worlds rviz
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
