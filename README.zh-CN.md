<div align='center'>
  <img src='./doc/logo.png'/>
</div>

<div align='center'>
  <a href='./README.md'>English</a> | 中文
</div>

---

This is a test case repository for [mapf_ros](https://github.com/speedzjy/mapf_ros) package.

The robot used for the simulation test is **ridgeback**, the official website address is at [https://clearpathrobotics.com/assets/guides/melodic/ridgeback/index.html](https://clearpathrobotics.com/assets/guides/melodic/ridgeback/index.html). The official tutorial introduces the mapping and planning operations of a single robot in detail. After you are familiar with the process, you can clone this repository for multi-robot testing.


# Dependences
This package has only been tested on **Ubuntu 18.04**

- [navigation](https://github.com/ros-planning/navigation)
  - ```sudo apt install ros-melodic-navigation```
- [teb_local_planner](https://github.com/rst-tu-dortmund/teb_local_planner)
  - download code and build: ```catkin_make```
- [ridgeback_simulater](https://github.com/ridgeback/ridgeback_simulator)
  - ```sudo apt install ros-melodic-ridgeback-simulator```

# Build
```
catkin_make
```

# Run

## quick start
- bringup
```
roslaunch ridgeback_test multi_ridgeback_world.launch
```
- amcl and move_base node
```
roslaunch ridgeback_navigation multi_nav.launch
```
- mapf
```
roslaunch mapf_base mapf_example.launch
```

<div align='center'>
  <img src='./doc/quickstart.png'/>
</div>

As shown in the figure, the first four buttons are traditional navigation buttons, which are used to control the positioning and movement of the two robots, and the last two buttons are used to send mapf targets to the mapf_base node.

After sending the mapf target point using the last two buttons, run:
```
rostopic pub --once /mapf_base/goal_init_flag std_msgs/Bool "data: true"
```
then the mapf_base node will generate a global plan

## mapping

Use a single robot to build a map.

- bringup
```
roslaunch ridgeback_test ridgeback_world.launch
```
- mapping
  - dependences: [slam_karto](https://github.com/ros-perception/slam_karto), [open_karto](https://github.com/ros-perception/open_karto)
```
roslaunch ridgeback_navigation karto_demo.launch
``` 
You can also use gmapping.

**Notes:** The mapping process produces both low-resolution and high-resolution maps

- save:
  - high-resolution map: ```rosrun map_server map_saver map:=/map -f ./mymap```
  - low-resolution map: ```rosrun map_server map_saver map:=/map_low_resolution -f ./mymap_low_reso```

**Notes:**
Since the low-resolution map and the high-resolution map do not completely overlap, the **origin** param in the **mymap_low_reso.yaml** file needs to be modified appropriately to make the two maps appear to overlap.

## Run mapf with new map
- change the high-resolution map name in [multi_nav_single.launch](https://github.com/speedzjy/ridgeback_mapf/blob/main/ridgeback_navigation/multi_launch/multi_nav_single.launch)
- change the low-resolution map name in [mapf_example.launch](https://github.com/speedzjy/mapf_ros/blob/main/mapf_base/launch/mapf_example.launch)

Then follow the quickstart steps.