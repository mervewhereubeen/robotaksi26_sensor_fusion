from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    pkg_dir = get_package_share_directory('robot_fusion')
    config_file = os.path.join(pkg_dir, 'config', 'ukf_config.yaml')
    
    return LaunchDescription([
        # IMU Covariance Injector
        Node(
            package='robot_fusion',
            executable='imu_cov_injector',
            name='imu_cov_injector',
            output='screen',
            parameters=[{
                'debug': True,
                'print_diagnostics': True,
                'input_topic': '/imu/data',
                'output_topic': '/imu/with_covariance',
                'imu_frame': 'imu_link',
                'base_frame': 'base_link',
                'publish_tf': True
        }]

        ),

        # ZED Covariance Injector
        Node(
            package='robot_fusion',
            executable='zed_cov_injector',
            name='zed_cov_injector',
            output='screen',
            parameters=[{
                'input_topic': '/zed/zed_node/odom',
                'output_topic': '/zed/zed_node/odom_with_covariance',
            }]
        ),

        # Static TF: base_link -> zed_camera_link (GÜNCELLENEN GERÇEK KOORDİNATLAR)
        Node(
            package='tf2_ros', 
            executable='static_transform_publisher',
            name='zed_static_tf',
            output='screen',
            arguments=['-0.205', '0.0', '0.685', '0.0', '0.0', '0.0', 'base_link', 'zed_camera_link']
        ),
        
        # Static TF: base_link -> velodyne (YENİ - LIDAR TRANSFORM)
        Node(
            package='tf2_ros', 
            executable='static_transform_publisher',
            name='lidar_static_tf',
            output='screen',
            arguments=['-0.177', '0.0', '0.620', '0.0', '0.0', '0.0', 'base_link', 'velodyne']
        ),
        
        # UKF Node
        Node(
            package='robot_localization',
            executable='ukf_node',
            name='ukf_filter_node',
            output='screen',
            parameters=[config_file],
            remappings=[
                ('/odometry/filtered', '/ukf/odometry')
            ]
        )
    ])
