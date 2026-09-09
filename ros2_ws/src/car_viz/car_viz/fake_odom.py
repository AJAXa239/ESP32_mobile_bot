#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster


class FakeOdom(Node):
    """
    Estimates robot pose by integrating /cmd_vel over time (open-loop
    dead reckoning - no real encoder feedback). Good enough to visualize
    driving behavior in RViz, but will drift from the real position over
    time since it has no ground-truth correction.
    """

    def __init__(self):
        super().__init__('fake_odom')

        self.declare_parameter('wheel_radius', 0.03)   # meters
        self.declare_parameter('wheel_separation', 0.18)  # meters, track width

        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.wheel_separation = self.get_parameter('wheel_separation').value

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.wheel_angle_left = 0.0
        self.wheel_angle_right = 0.0

        self.linear_x = 0.0
        self.angular_z = 0.0

        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.last_time = self.get_clock().now()
        self.timer = self.create_timer(0.05, self.update)  # 20Hz

        self.get_logger().info('fake_odom started - integrating /cmd_vel for visualization')

    def cmd_callback(self, msg: Twist):
        self.linear_x = msg.linear.x
        self.angular_z = msg.angular.z

    def update(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        if dt <= 0.0:
            return

        # Integrate pose
        self.theta += self.angular_z * dt
        self.x += self.linear_x * math.cos(self.theta) * dt
        self.y += self.linear_x * math.sin(self.theta) * dt

        # Differential-drive wheel speeds
        v_left = self.linear_x - (self.angular_z * self.wheel_separation / 2.0)
        v_right = self.linear_x + (self.angular_z * self.wheel_separation / 2.0)

        wheel_vel_left = v_left / self.wheel_radius
        wheel_vel_right = v_right / self.wheel_radius

        self.wheel_angle_left += wheel_vel_left * dt
        self.wheel_angle_right += wheel_vel_right * dt

        # Quaternion from yaw
        qz = math.sin(self.theta / 2.0)
        qw = math.cos(self.theta / 2.0)

        # Publish odom -> base_link TF
        t = TransformStamped()
        t.header.stamp = now.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.04  # lift so wheel bottoms rest on the ground plane
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

        # Publish Odometry message
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.04
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = self.linear_x
        odom.twist.twist.angular.z = self.angular_z
        self.odom_pub.publish(odom)

        # Publish wheel joint states so the URDF wheels visually spin
        js = JointState()
        js.header.stamp = now.to_msg()
        js.name = [
            'wheel_front_left_joint',
            'wheel_rear_left_joint',
            'wheel_front_right_joint',
            'wheel_rear_right_joint',
        ]
        js.position = [
            self.wheel_angle_left,
            self.wheel_angle_left,
            self.wheel_angle_right,
            self.wheel_angle_right,
        ]
        self.joint_pub.publish(js)


def main(args=None):
    rclpy.init(args=args)
    node = FakeOdom()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
