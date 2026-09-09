#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('car_viz')
    urdf_path = os.path.join(pkg_share, 'urdf', 'car.urdf')
    rviz_config_path = os.path.join(pkg_share, 'rviz', 'car_view.rviz')

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    fake_odom_node = Node(
        package='car_viz',
        executable='fake_odom',
        name='fake_odom',
        output='screen',
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
    )

    return LaunchDescription([
        robot_state_publisher_node,
        fake_odom_node,
        rviz_node,
    ])
