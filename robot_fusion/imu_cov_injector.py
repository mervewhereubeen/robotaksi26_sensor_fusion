#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
import copy

class ImuCovInjector(Node):
    def __init__(self):
        super().__init__('imu_cov_injector')

        # Parameters
        self.declare_parameter('input_topic', '/imu/data')
        self.declare_parameter('output_topic', '/imu/with_covariance')
        self.declare_parameter('imu_frame', 'imu_link')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('time_offset', 0.0)

        # BALANCED COVARIANCE - PROVEN WORKING!
        self.orientation_cov = [0.02, 0.0, 0.0,      # BALANCED
                                0.0, 0.02, 0.0,       # BALANCED
                                0.0, 0.0, 0.06]      # BALANCED

        # ANGULAR VELOCITY: VERY LOW TRUST (prevents turn spikes)
        self.angular_vel_cov = [1.0, 0.0, 0.0,       # LOW TRUST
                                0.0, 1.0, 0.0,
                                0.0, 0.0, 1.0]

        # LINEAR ACCELERATION: VERY LOW TRUST
        self.linear_acc_cov = [2.0, 0.0, 0.0,        # LOW TRUST
                               0.0, 2.0, 0.0,
                               0.0, 0.0, 2.0]

        # Get parameters
        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.time_offset = self.get_parameter('time_offset').get_parameter_value().double_value

        # Publisher & Subscriber
        self.publisher = self.create_publisher(Imu, output_topic, 10)
        self.subscription = self.create_subscription(Imu, input_topic, self.imu_callback, 10)

        # TF broadcaster
        self.publish_tf = self.get_parameter('publish_tf').get_parameter_value().bool_value
        if self.publish_tf:
            self.br = TransformBroadcaster(self)

        # Real vehicle IMU position
        self.tf_msg = TransformStamped()
        self.tf_msg.header.frame_id = self.get_parameter('base_frame').get_parameter_value().string_value
        self.tf_msg.child_frame_id = self.get_parameter('imu_frame').get_parameter_value().string_value
        self.tf_msg.transform.translation.x = 1.44
        self.tf_msg.transform.translation.y = 0.0
        self.tf_msg.transform.translation.z = 1.39
        self.tf_msg.transform.rotation.x = 0.0
        self.tf_msg.transform.rotation.y = 0.0
        self.tf_msg.transform.rotation.z = 0.0
        self.tf_msg.transform.rotation.w = 1.0

        # Timestamp tracking
        self.last_timestamp = None
        self.max_time_gap = 0.3
        self.msg_count = 0

        self.get_logger().info('IMU Covariance Injector started - STABLE WORKING CONFIG!')

    def imu_callback(self, msg):
        try:
            self.msg_count += 1
            
            # Timestamp kontrolü
            current_time = msg.header.stamp
            
            if self.last_timestamp is not None:
                time_diff = (current_time.sec + current_time.nanosec * 1e-9) - \
                           (self.last_timestamp.sec + self.last_timestamp.nanosec * 1e-9)
                
                if time_diff > self.max_time_gap:
                    self.get_logger().warn(f'Large time gap detected: {time_diff:.3f}s')
                elif time_diff < 0:
                    self.get_logger().warn('Negative time difference detected')
                    return
            
            self.last_timestamp = current_time
            
            imu_msg = copy.deepcopy(msg)
            
            # Time offset uygula
            if self.time_offset != 0.0:
                offset_ns = int(self.time_offset * 1e9)
                new_nanosec = imu_msg.header.stamp.nanosec + offset_ns
                
                if new_nanosec >= 1e9:
                    imu_msg.header.stamp.sec += 1
                    imu_msg.header.stamp.nanosec = int(new_nanosec - 1e9)
                elif new_nanosec < 0:
                    imu_msg.header.stamp.sec -= 1
                    imu_msg.header.stamp.nanosec = int(new_nanosec + 1e9)
                else:
                    imu_msg.header.stamp.nanosec = int(new_nanosec)
            
            # Add PROVEN WORKING covariance matrices
            imu_msg.orientation_covariance = self.orientation_cov
            imu_msg.angular_velocity_covariance = self.angular_vel_cov
            imu_msg.linear_acceleration_covariance = self.linear_acc_cov

            # Publish processed IMU
            self.publisher.publish(imu_msg)

            # Publish TF transform
            if self.publish_tf:
                self.tf_msg.header.stamp = imu_msg.header.stamp
                self.br.sendTransform(self.tf_msg)

            # Her 500 mesajda bir bilgi ver
            if self.msg_count % 500 == 0:
                self.get_logger().info(f'Processed {self.msg_count} IMU messages - STABLE!')

        except Exception as e:
            self.get_logger().error(f'Error processing IMU: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = ImuCovInjector()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        node.get_logger().error(f'Unexpected error: {str(e)}')
    finally:
        try:
            node.destroy_node()
        except:
            pass
        try:
            rclpy.shutdown()
        except:
            pass

if __name__ == '__main__':
    main()
