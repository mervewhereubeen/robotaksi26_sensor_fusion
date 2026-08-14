#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import copy


class ZedCovInjector(Node):
    """
    The ZED wrapper publishes /zed/zed_node/odom with a pose covariance
    diagonal of ~1e-10 on every message. robot_localization's odomN_config
    has no supported "pose_covariance_override" parameter (the key present
    in ukf_config.yaml is silently ignored), so the UKF was fusing that raw
    1e-10 covariance directly, which drives the position Kalman gain to
    ~1 every update and destabilizes the correlated velocity states.

    This node republishes the same odometry with the pose covariance that
    was already chosen (but never actually applied) in the old
    odom0_pose_covariance_override block of ukf_config.yaml.
    """

    def __init__(self):
        super().__init__('zed_cov_injector')

        self.declare_parameter('input_topic', '/zed/zed_node/odom')
        self.declare_parameter('output_topic', '/zed/zed_node/odom_with_covariance')

        # Values carried over from the dead odom0_pose_covariance_override
        # block (x, y, z, roll, pitch, yaw). Roll/pitch are left at a high
        # variance since they are not fused by the UKF.
        self.pose_cov_diag = [0.02, 0.02, 0.04, 1000000.0, 1000000.0, 0.06]

        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value

        self.publisher = self.create_publisher(Odometry, output_topic, 10)
        self.subscription = self.create_subscription(Odometry, input_topic, self.odom_callback, 10)

        self.msg_count = 0
        self.get_logger().info(
            f'ZED covariance injector started: {input_topic} -> {output_topic}'
        )

    def odom_callback(self, msg):
        try:
            self.msg_count += 1

            odom_msg = copy.deepcopy(msg)

            pose_cov = [0.0] * 36
            for i in range(6):
                pose_cov[i * 6 + i] = self.pose_cov_diag[i]
            odom_msg.pose.covariance = pose_cov

            self.publisher.publish(odom_msg)

            if self.msg_count % 500 == 0:
                self.get_logger().info(f'Processed {self.msg_count} ZED odometry messages')

        except Exception as e:
            self.get_logger().error(f'Error processing ZED odometry: {str(e)}')


def main(args=None):
    rclpy.init(args=args)
    node = ZedCovInjector()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f'Unexpected error: {str(e)}')
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
