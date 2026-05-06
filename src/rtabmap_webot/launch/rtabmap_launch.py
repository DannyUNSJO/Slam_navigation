import os
import launch

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node

from ament_index_python.packages import (
    get_package_share_directory,
    get_packages_with_prefixes
)

from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.wait_for_controller_connection import WaitForControllerConnection


def generate_launch_description():

    pkg_dir = get_package_share_directory('rtabmap_webot')

    # -------------------------------------------------
    # Launch configurations
    # -------------------------------------------------

    mode = LaunchConfiguration('mode')
    use_rviz = LaunchConfiguration('rviz', default=True)
    use_nav = LaunchConfiguration('nav', default=False)
    use_sim_time = LaunchConfiguration('use_sim_time', default=True)
    enable_markers = LaunchConfiguration('marker', default=True)
    use_rtabmap = LaunchConfiguration('rtabmap', default=True)

    declare_mode_arg = DeclareLaunchArgument(
        'mode',
        default_value='realtime',
        description='Webots simulation mode'
    )

    declare_marker_arg = DeclareLaunchArgument(
        'marker',
        default_value='true',
        description='Enable building marker'
    )

    declare_nav_arg = DeclareLaunchArgument(
        'nav',
        default_value='false',
        description='Enable Navigation2'
    )

    declare_rtabmap_arg = DeclareLaunchArgument(
        'rtabmap',
        default_value='true',
        description='Enable RTAB-Map SLAM'
    )

    # -------------------------------------------------
    # Webots
    # -------------------------------------------------

    world_file = PathJoinSubstitution([
        pkg_dir,
        'worlds',
        'sg_NTUST_HWH.wbt'
    ])

    webots = WebotsLauncher(
        world=world_file,
        mode=mode,
        ros2_supervisor=True
    )

    # -------------------------------------------------
    # Robot State Publisher
    # -------------------------------------------------

    robot_description_path = os.path.join(
        pkg_dir,
        'resource',
        'tiago_webots.urdf'
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': open(robot_description_path).read(),
            'use_sim_time': use_sim_time
        }]
    )

    # -------------------------------------------------
    # TF base_link → base_footprint
    # -------------------------------------------------

    footprint_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=[
            '0', '0', '0',
            '0', '0', '0',
            'base_link',
            'base_footprint'
        ],
        output='screen'      
    )

    # -------------------------------------------------
    # ROS2 Control
    # -------------------------------------------------

    controller_manager_timeout = [
        '--controller-manager-timeout',
        '500'
    ]

    controller_manager_prefix = 'python.exe' if os.name == 'nt' else ''

    diffdrive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        prefix=controller_manager_prefix,
        arguments=['diffdrive_controller'] + controller_manager_timeout
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        prefix=controller_manager_prefix,
        arguments=['joint_state_broadcaster'] + controller_manager_timeout
    )

    ros_control_spawners = [
        diffdrive_controller_spawner,
        joint_state_broadcaster_spawner
    ]

    # -------------------------------------------------
    # Webots Controller
    # -------------------------------------------------

    ros2_control_params = os.path.join(
        pkg_dir,
        'resource',
        'ros2_control.yml'
    )

    mappings = [
        ('/diffdrive_controller/cmd_vel_unstamped', '/cmd_vel'),
        ('/diffdrive_controller/odom', '/odom')
    ]

    tiago_driver = WebotsController(
        robot_name='Tiago_Lite',
        parameters=[
            {
                'robot_description': robot_description_path,
                'use_sim_time': use_sim_time,
                'set_robot_state_publisher': True
            },
            ros2_control_params
        ],
        remappings=mappings,
        respawn=True
    )

    # -------------------------------------------------
    # RTAB-Map SLAM (LiDAR)
    # -------------------------------------------------

    rtabmap_params = {
        'frame_id': 'base_link',
        'odom_frame_id': 'odom',
        'map_frame_id': 'map',
        'Rtabmap/DetectionRate': '2.5', # 每秒更新幾次map

        'publish_tf': True,
        'publish_map': True,  # 建議加上

        'subscribe_scan': True,
        'subscribe_scan_cloud': False,
        'subscribe_depth': False,
        'subscribe_rgb': False,

        'Reg/Strategy': '1',
        'Reg/Force3DoF': 'True',
        'RGBD/LinearUpdate': '0.01',       # 每移動0.0c1m更新一次
        'RGBD/AngularUpdate': '1.0',      # 每旋轉5°更新一次

        'Grid/FromDepth': 'False',
        'Grid/3D': 'True',  
        'Grid/RangeMax': '10.0',
        'Grid/Sensor': '0',

        'use_sim_time': True
    }

    db_path = os.path.expanduser('~/.ros/rtabmap.db')
    if os.path.exists(db_path):
        os.remove(db_path)

    rtabmap_node = Node(
        package='rtabmap_slam',
        executable='rtabmap',
        name='rtabmap',
        output='screen',
        parameters=[rtabmap_params],
        remappings=[
            ('scan', '/scan'),
            ('odom', '/odom'),
            ('tf', '/tf'),
            ('tf_static', '/tf_static')
        ],
        condition=launch.conditions.IfCondition(use_rtabmap)
    )

    # -------------------------------------------------
    # Navigation2 (optional)
    # -------------------------------------------------

    navigation_nodes = []

    if 'nav2_bringup' in get_packages_with_prefixes():

        nav2_params = os.path.join(
            pkg_dir,
            'resource',
            'nav2_params.yaml'
        )

        navigation_nodes.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(
                        get_package_share_directory('nav2_bringup'),
                        'launch',
                        'bringup_launch.py'
                    )
                ),
                launch_arguments=[
                    ('params_file', nav2_params),
                    ('use_sim_time', use_sim_time)
                ],
                condition=launch.conditions.IfCondition(use_nav)
            )
        )

    # -------------------------------------------------
    # RViz
    # -------------------------------------------------

    rviz_config = os.path.join(
        pkg_dir,
        'resource',
        'default.rviz'
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['--display-config=' + rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=launch.conditions.IfCondition(use_rviz)
    )

    # -------------------------------------------------
    # Marker Node
    # -------------------------------------------------

    markers_node = Node(
        package='rtabmap_webot',
        executable='buildings_marker',
        name='buildings_marker',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        condition=launch.conditions.IfCondition(enable_markers)
    )

    # -------------------------------------------------
    # Wait for Webots controller
    # -------------------------------------------------

    waiting_nodes = WaitForControllerConnection(
        target_driver=tiago_driver,
        nodes_to_start=[
            rviz,
            rtabmap_node,
            markers_node
        ] + navigation_nodes + ros_control_spawners
    )

    # -------------------------------------------------
    # Launch Description
    # -------------------------------------------------

    return LaunchDescription([
        declare_mode_arg,
        declare_marker_arg,
        declare_nav_arg,
        declare_rtabmap_arg,

        webots,
        webots._supervisor,

        robot_state_publisher,
        footprint_publisher,

        tiago_driver,
        waiting_nodes,

        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=webots,
                on_exit=[
                    launch.actions.EmitEvent(
                        event=launch.events.Shutdown()
                    )
                ]
            )
        )
    ])