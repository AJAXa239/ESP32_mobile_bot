#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import termios
import tty
import select


INSTRUCTIONS = """
WASD Teleop
-----------
w : forward
s : backward
a : turn left
d : turn right
x : stop
q : quit

Hold a key to keep moving. Releasing stops after ~0.3s (safety).
"""


class WasdTeleop(Node):
    def __init__(self):
        super().__init__('wasd_teleop')

        self.declare_parameter('max_linear', 0.5)
        self.declare_parameter('max_angular', 1.0)
        self.max_linear = self.get_parameter('max_linear').get_parameter_value().double_value
        self.max_angular = self.get_parameter('max_angular').get_parameter_value().double_value

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.linear = 0.0
        self.angular = 0.0

        self.timer = self.create_timer(0.1, self.publish_cmd)  # 10Hz

    def publish_cmd(self):
        msg = Twist()
        msg.linear.x = self.linear
        msg.angular.z = self.angular
        self.publisher_.publish(msg)


def get_key(settings, timeout=0.1):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main(args=None):
    rclpy.init(args=args)
    node = WasdTeleop()

    print(INSTRUCTIONS)

    settings = termios.tcgetattr(sys.stdin)

    try:
        while rclpy.ok():
            key = get_key(settings, timeout=0.1)

            if key == 'w':
                node.linear = node.max_linear
                node.angular = 0.0
            elif key == 's':
                node.linear = -node.max_linear
                node.angular = 0.0
            elif key == 'a':
                node.linear = 0.0
                node.angular = node.max_angular
            elif key == 'd':
                node.linear = 0.0
                node.angular = -node.max_angular
            elif key == 'x':
                node.linear = 0.0
                node.angular = 0.0
            elif key == 'q':
                break
            elif key == '':
                # no key pressed this cycle - stop (acts like "release to stop")
                node.linear = 0.0
                node.angular = 0.0

            rclpy.spin_once(node, timeout_sec=0)

    except Exception as e:
        print(e)
    finally:
        # Always stop the robot on exit
        stop_msg = Twist()
        node.publisher_.publish(stop_msg)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
