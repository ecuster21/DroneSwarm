"""Launch the full swarm reconnaissance stack."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _build_nodes(context):
    num_drones = int(LaunchConfiguration('num_drones').perform(context))
    first_instance = int(LaunchConfiguration('first_instance').perform(context))
    system_id_offset = int(
        LaunchConfiguration('system_id_offset').perform(context)
    )
    namespace_prefix = LaunchConfiguration('namespace_prefix').perform(context)

    actions = []
    for index in range(num_drones):
        instance_id = first_instance + index
        target_system = instance_id + system_id_offset
        namespace = f'{namespace_prefix}{instance_id}'
        actions.append(
            Node(
                package='offboard_py',
                executable='offboard_control',
                name=f'offboard_control_{instance_id}',
                namespace=namespace,
                output='screen',
                parameters=[
                    {
                        'target_z': LaunchConfiguration('survey_altitude_z'),
                        'command_target_system': target_system,
                        'acceptance_radius_m': LaunchConfiguration(
                            'acceptance_radius_m'
                        ),
                    }
                ],
            )
        )

    actions.append(
        Node(
            package='swarm_logic',
            executable='swarm_recon_controller',
            name='swarm_recon_controller',
            output='screen',
            parameters=[
                {
                    'num_drones': LaunchConfiguration('num_drones'),
                    'first_instance': LaunchConfiguration('first_instance'),
                    'namespace_prefix': LaunchConfiguration('namespace_prefix'),
                    'system_id_offset': LaunchConfiguration('system_id_offset'),
                    'group_size': LaunchConfiguration('group_size'),
                    'origin_x': LaunchConfiguration('origin_x'),
                    'origin_y': LaunchConfiguration('origin_y'),
                    'width_m': LaunchConfiguration('width_m'),
                    'height_m': LaunchConfiguration('height_m'),
                    'heading_rad': LaunchConfiguration('heading_rad'),
                    'staging_offset_m': LaunchConfiguration('staging_offset_m'),
                    'staging_spacing_m': LaunchConfiguration('staging_spacing_m'),
                    'survey_altitude_z': LaunchConfiguration('survey_altitude_z'),
                    'survey_speed_mps': LaunchConfiguration('survey_speed_mps'),
                    'acceptance_radius_m': LaunchConfiguration(
                        'acceptance_radius_m'
                    ),
                    'takeoff_acceptance_m': LaunchConfiguration(
                        'takeoff_acceptance_m'
                    ),
                    'command_timeout_sec': LaunchConfiguration(
                        'command_timeout_sec'
                    ),
                    'startup_wait_timeout_sec': LaunchConfiguration(
                        'startup_wait_timeout_sec'
                    ),
                    'spawn_x_m': LaunchConfiguration('spawn_x_m'),
                    'spawn_y_base_m': LaunchConfiguration('spawn_y_base_m'),
                    'spawn_y_step_m': LaunchConfiguration('spawn_y_step_m'),
                    'reassign_on_prestart_failure': LaunchConfiguration(
                        'reassign_on_prestart_failure'
                    ),
                }
            ],
        )
    )

    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument('num_drones', default_value='20'),
            DeclareLaunchArgument('first_instance', default_value='1'),
            DeclareLaunchArgument('namespace_prefix', default_value='px4_'),
            DeclareLaunchArgument('system_id_offset', default_value='1'),
            DeclareLaunchArgument('group_size', default_value='5'),
            DeclareLaunchArgument('origin_x', default_value='50.0'),
            DeclareLaunchArgument('origin_y', default_value='0.0'),
            DeclareLaunchArgument('width_m', default_value='80.0'),
            DeclareLaunchArgument('height_m', default_value='120.0'),
            DeclareLaunchArgument('heading_rad', default_value='0.0'),
            DeclareLaunchArgument('staging_offset_m', default_value='20.0'),
            DeclareLaunchArgument('staging_spacing_m', default_value='6.0'),
            DeclareLaunchArgument('survey_altitude_z', default_value='-10.0'),
            DeclareLaunchArgument('survey_speed_mps', default_value='4.0'),
            DeclareLaunchArgument('acceptance_radius_m', default_value='2.0'),
            DeclareLaunchArgument('takeoff_acceptance_m', default_value='1.0'),
            DeclareLaunchArgument('command_timeout_sec', default_value='5.0'),
            DeclareLaunchArgument('startup_wait_timeout_sec', default_value='15.0'),
            DeclareLaunchArgument('spawn_x_m', default_value='0.0'),
            DeclareLaunchArgument('spawn_y_base_m', default_value='0.0'),
            DeclareLaunchArgument('spawn_y_step_m', default_value='3.0'),
            DeclareLaunchArgument(
                'reassign_on_prestart_failure',
                default_value='true',
            ),
            OpaqueFunction(function=_build_nodes),
        ]
    )
