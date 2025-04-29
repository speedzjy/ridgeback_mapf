from setuptools import find_packages, setup

package_name = 'docking_tf'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='speed',
    maintainer_email='speed@docker.com',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'docking_tf_pose = docking_tf.docking_tf_pose:main',
            'docking_tf_broadcaster = docking_tf.docking_tf_broadcaster:main',
        ],
    },
)
