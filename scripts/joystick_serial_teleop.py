#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial
import threading


class JoystickSerialTeleop(Node):
    def __init__(self):
        super().__init__('joystick_serial_teleop')

        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('max_linear', 0.5)   # m/s equivalent, scales to -1..1 anyway
        self.declare_parameter('max_angular', 1.0)

        port = self.get_parameter('serial_port').get_parameter_value().string_value
        baud = self.get_parameter('baud_rate').get_parameter_value().integer_value
        self.max_linear = self.get_parameter('max_linear').get_parameter_value().double_value
        self.max_angular = self.get_parameter('max_angular').get_parameter_value().double_value

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)

        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.get_logger().info(f'Opened serial port {port} at {baud} baud')
        except serial.SerialException as e:
            self.get_logger().error(f'Could not open serial port {port}: {e}')
            self.ser = None
            return

        self.last_x = 0.0
        self.last_y = 0.0
        self.last_btn = 0

        # Read serial in a background thread so it doesn't block ROS2 spinning
        self.running = True
        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()

        # Publish at a steady rate regardless of serial read timing
        self.timer = self.create_timer(0.05, self.publish_cmd)  # 20Hz

    def read_loop(self):
        while self.running:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) != 4:
                    continue
                x_raw = int(parts[0])   # 0-1023, center ~512
                y_raw = int(parts[1])   # 0-1023, center ~512
                button = int(parts[2])  # 0 = pressed, 1 = released
                estop = int(parts[3])   # 0 = pressed, 1 = released

                x_centered = x_raw - 512
                y_centered = 512 - y_raw

                # Normalize -512..511 -> -1.0..1.0
                self.last_x = max(-1.0, min(1.0, x_centered / 512.0))
                self.last_y = max(-1.0, min(1.0, y_centered / 512.0))
                # Only ESTOP triggers a stop for now - the BUTTON pin is
                # reading stuck LOW on this board (wiring issue to debug
                # separately), so it's ignored here to avoid a permanent stop.
                self.last_btn = 1 if estop == 0 else 0

            except (ValueError, UnicodeDecodeError):
                continue
            except serial.SerialException as e:
                self.get_logger().error(f'Serial read error: {e}')
                break

    def publish_cmd(self):
        if self.ser is None:
            return

        msg = Twist()

        # Emergency stop on button press
        if self.last_btn == 1:
            msg.linear.x = 0.0
            msg.angular.z = 0.0
        else:
            # Deadzone
            x = self.last_x if abs(self.last_x) > 0.05 else 0.0
            y = self.last_y if abs(self.last_y) > 0.05 else 0.0

            msg.linear.x = y * self.max_linear
            msg.angular.z = -x * self.max_angular  # negative so joystick-right = turn right

        self.publisher_.publish(msg)

    def destroy_node(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.ser:
            self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = JoystickSerialTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
