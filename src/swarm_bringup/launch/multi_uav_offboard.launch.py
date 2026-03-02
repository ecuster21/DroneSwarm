"""Launch configurable offboard controllers for PX4 multi-instance SITL."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _build_nodes(context):
    num_drones = int(LaunchConfiguration('num_drones').perform(context))
    spacing = float(LaunchConfiguration('spacing').perform(context))
    start_x = float(LaunchConfiguration('start_x').perform(context))
    start_y = float(LaunchConfiguration('start_y').perform(context))
    altitude = float(LaunchConfiguration('altitude').perform(context))
    yaw = float(LaunchConfiguration('yaw').perform(context))
    namespace_prefix = LaunchConfiguration('namespace_prefix').perform(context)
    first_instance = int(LaunchConfiguration('first_instance').perform(context))
    system_id_offset = int(
        LaunchConfiguration('system_id_offset').perform(context)
    )

    actions = []
    for index in range(num_drones):
        instance_id = first_instance + index
        target_system = instance_id + system_id_offset
        namespace = f'{namespace_prefix}{instance_id}'
        target_y = start_y + spacing * index
        actions.append(
            Node(
                package='offboard_py',
                executable='offboard_control',
                name=f'offboard_control_{instance_id}',
                namespace=namespace,
                output='screen',
                parameters=[
                    {
                        'target_x': start_x,
                        'target_y': target_y,
                        'target_z': altitude,
                        'target_yaw': yaw,
                        'command_target_system': target_system,
                    }
                ],
            )
        )

    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument('num_drones', default_value='3'),
            DeclareLaunchArgument('spacing', default_value='3.0'),
            DeclareLaunchArgument('start_x', default_value='0.0'),
            DeclareLaunchArgument('start_y', default_value='0.0'),
            DeclareLaunchArgument('altitude', default_value='-5.0'),
            DeclareLaunchArgument('yaw', default_value='-3.14'),
            DeclareLaunchArgument('namespace_prefix', default_value='px4_'),
            DeclareLaunchArgument('first_instance', default_value='1'),
            DeclareLaunchArgument('system_id_offset', default_value='1'),
            OpaqueFunction(function=_build_nodes),
        ]
    )
