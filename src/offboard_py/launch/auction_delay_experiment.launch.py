"""Reproducible experiment with deterministic delay and jitter injection."""

from os import path

from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from offboard_py.experiment_profiles import launch_arguments_for_profile
from offboard_py.experiment_profiles import typed_parameters_for_profile


PROFILE_NAME = 'delay'


def generate_launch_description():
    """Launch the delay-focused experiment profile."""
    launch_arguments = launch_arguments_for_profile(PROFILE_NAME)
    launch_arguments.update({
        'enable_metrics': 'true',
        'metrics_output_dir': 'experiment_results/delay',
        'experiment_profile': PROFILE_NAME,
    })
    typed_parameters = typed_parameters_for_profile(PROFILE_NAME)
    launch_file = path.join(
        get_package_share_directory('offboard_py'),
        'launch',
        'auction_sitl.launch.py',
    )
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_file),
            launch_arguments=launch_arguments.items(),
        ),
        Node(
            package='offboard_py',
            executable='experiment_logger',
            name='experiment_logger',
            parameters=[
                {
                    'profile_name': PROFILE_NAME,
                    'output_dir': 'experiment_results/delay',
                    **typed_parameters,
                }
            ],
            output='screen',
        ),
    ])
