<div align='center'>
  <img src='./doc/ridgeback_demo.gif'/>
</div>

<div align='center'>
  <a href='./README.md'>English</a> | 中文
</div>

---

这是一个用于 [mapf_ros](https://github.com/speedzjy/mapf_ros) 包的测试案例仓库。

仿真测试使用的机器人是 **ridgeback**，它支持 **全向** 移动，官方网址在 [clearpath](https://docs.clearpathrobotics.com/docs/ros/)。官方教程详细介绍了单个机器人的建图和规划操作。熟悉该过程后，您可以克隆此仓库进行多机器人测试。


# 依赖
此功能包仅在 **Ubuntu 22.04** 的 **ROS humble** 上进行过测试。

[nav2](https://github.com/ros-navigation/navigation2) | [clearpath](https://github.com/clearpathrobotics) | cartographer

```
sudo apt update
sudo apt install ros-humble-navigation2 ros-humble-clearpath-simulator
sudo apt install ros-humble-cartographer ros-humble-cartographer-ros
```

# Build
```
mkdir -p ros2_ws/src && cd ros2_ws/src
git clone --recurse-submodules -b humble https://github.com/speedzjy/ridgeback_mapf.git 
cd ..
colcon build --symlink-install
```

# Run

## 快速开始
- 参数文件准备

在根目录(~)下创建clearpath文件夹和各机器人子文件夹，并将以下机器人配置文件命名为 `robot.yaml` 放入各子文件夹，其中，配置文件的 `ros2:namespace` 字段需要以 `rb_` 加上数字 (例如, `rb_0`, `rb_1`).

```
serial_number: r100-0000
version: 0
system:
  hosts:
    - hostname: cpr-r100-0000
      ip: 192.168.131.1
  ros2:
    namespace: rb_0
sensors:
  lidar2d:
    - model: sick_lms1xx
      parent: chassis_link
      xyz: [0.3455, 0.0, 0.1977]
    - model: sick_lms1xx
      parent: chassis_link
      xyz: [-0.3455, 0.0, 0.1977]
      rpy: [0.0, 0.0, 3.14159]

```

目录树结构如下:
```
$ tree -L 3
.
|-- clearpath
|   |-- rb_0
|   |   `-- robot.yaml
|   |-- rb_1
|   |   `-- robot.yaml
```

然后生成配置文件:
```
ros2 launch multi_ridgeback_sim yield_robot_description.launch.py
```


- 启动
```
ros2 launch multi_ridgeback_sim multi_rb_bringup.launch.py
```
- 导航定位
```
ros2 launch multi_ridgeback_sim multi_localization.launch.py
```
- mapf
```
ros2 launch mapf_base mapf_example.launch.py
```

<div align='center'>
  <img src='./doc/quickstart.jpg'/>
</div>

如图所示，rviz中的前两个按钮是传统的导航按钮，用于控制两个机器人的定位和移动，后两个按钮用于向 mapf_base 节点发送 mapf 目标点。

<div align='center'>
  <img src='./doc/goal_transformer.png'/>
</div>

使用后两个按钮发送 mapf 目标点后，运行：
```
ros2 topic pub --once /mapf/goal_init_flag std_msgs/msg/Bool "{data: true}"
```
然后 mapf_base 节点将生成全局规划路径，可以在 rviz 中进行可视化。

## 建图

使用单个机器人构建地图。

编辑 [multi_rb_bringup.launch.py](https://github.com/speedzjy/ridgeback_mapf/blob/humble/multi_ridgeback_sim/launch/bringup/multi_rb_bringup.launch.py)

注释掉 `ROBOT_LIST` 中除 `rb_0` 之外的所有行

- bringup
```
ros2 launch multi_ridgeback_sim multi_rb_bringup.launch.py
```
- mapping
```
ros2 launch multi_ridgeback_sim cartographer.launch.py
``` 

保存地图:
```
ros2 service call /rb_0/finish_trajectory cartographer_ros_msgs/srv/FinishTrajectory "{trajectory_id: 0}"
ros2 run nav2_map_server map_saver_cli -t /rb_0/map -f mymap
```

**注意:**

构建地图后，将高分辨率地图转换为低分辨率地图。

```
sudo apt install imagemagick
----------------------------
convert input.pgm -resize 50% output_low_resolution.pgm
```

如果低分辨率地图和高分辨率地图不完全重叠，则需要适当修改 **mymap_low_reso.yaml** 文件中的 **origin** 参数，以使两个地图看起来重叠。

## 使用新地图运行 mapf
- 修改 [localization.launch.py](https://github.com/speedzjy/ridgeback_mapf/blob/humble/multi_ridgeback_sim/launch/localization/localization.launch.py) 中的**高**分辨率地图名称
- 修改 [mapf_example.launch.py](https://github.com/speedzjy/mapf_ros/blob/humble/mapf_base/launch/mapf_example.launch.py) 中的**低**分辨率地图名称

然后按照快速开始的步骤进行操作。