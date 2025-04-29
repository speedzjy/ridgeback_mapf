from setuptools import find_packages, setup
import os
from glob import glob

package_name = "task_communication"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/station_cfg", ["station_cfg/station.json"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="speed",
    maintainer_email="speed@speed.com",
    description="TODO: Package description",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "platform_communication = task_communication.platform_communication:main",
            "save_pose = task_communication.save_pose:main",
            "rb_record_pose = task_communication.rb_record_pose:main",
        ],
    },
)
