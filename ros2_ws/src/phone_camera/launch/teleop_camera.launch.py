#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Declare arguments for micro-ROS agent
    agent_port = LaunchConfiguration('agent_port', default='8888')
    agent_ip = LaunchConfiguration('agent_ip', default='192.168.1.100')

    declare_agent_port_cmd = DeclareLaunchArgument(
        'agent_port',
        default_value='8888',
        description='Port for micro-ROS agent UDP server')

    declare_agent_ip_cmd = DeclareLaunchArgument(
        'agent_ip',
        default_value='192.168.1.100',
        description='IP address for micro-ROS agent')

    # Start micro-ROS agent
    start_micro_ros_agent_cmd = ExecuteProcess(
        cmd=['micro_ros_agent', 'udp4', '--port', agent_port],
        output='screen',
        name='micro_ros_agent')

    # Phone camera publisher node
    phone_camera_publisher_node = Node(
        package='phone_camera',
        executable='phone_camera_publisher',
        name='phone_camera_publisher',
        output='screen',
        parameters=[{'stream_url': 'http://192.168.1.50:8080/video'}])

    # Teleop twist keyboard node
    teleop_twist_keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='xterm -e',  # Open in a new terminal window
        remappings=[('/cmd_vel', '/cmd_vel')])

    # Create the launch description and populate
    ld = LaunchDescription()

    ld.add_action(declare_agent_port_cmd)
    ld.add_action(declare_agent_ip_cmd)
    ld.add_action(start_micro_ros_agent_cmd)
    ld.add_action(phone_camera_publisher_node)
    ld.add_action(teleop_twist_keyboard_node)

    return ld