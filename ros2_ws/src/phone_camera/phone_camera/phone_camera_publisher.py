#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2


class PhoneCameraPublisher(Node):
    def __init__(self):
        super().__init__('phone_camera_publisher')

        self.declare_parameter('stream_url', 'http://192.168.1.50:8080/video')
        stream_url = self.get_parameter('stream_url').get_parameter_value().string_value

        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)
        self.cap = cv2.VideoCapture(stream_url)

        if not self.cap.isOpened():
            self.get_logger().error(f'Could not open stream: {stream_url}')

        timer_period = 1.0 / 30.0  # 30 fps
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.build_image_msg(frame)
            self.publisher_.publish(msg)
        else:
            self.get_logger().warn('Failed to read frame from phone stream')

    def build_image_msg(self, frame):
        # Manually build sensor_msgs/Image to avoid a cv_bridge/numpy
        # dtype mismatch bug (KeyError in cv2_to_imgmsg on some setups).
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'phone_camera'
        msg.height = frame.shape[0]
        msg.width = frame.shape[1]
        msg.encoding = 'bgr8'
        msg.is_bigendian = 0
        msg.step = frame.shape[1] * frame.shape[2]
        msg.data = frame.tobytes()
        return msg

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PhoneCameraPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
