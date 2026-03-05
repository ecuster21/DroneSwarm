"""Launch the asynchronous auction stack for a small PX4 SITL swarm."""

from os import path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _to_bool(value: str) -> bool:
    """Convert a launch string into a bool."""
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _launch_setup(context, *args, **kwargs):
    """Create task board and per-UAV nodes from launch arguments."""
    del args
    del kwargs

    uav_count = max(1, int(LaunchConfiguration('uav_count').perform(context)))
    namespace_prefix = LaunchConfiguration('namespace_prefix').perform(context)
    base_update_period = LaunchConfiguration('update_period_sec').perform(context)
    drop_probability = LaunchConfiguration('drop_probability').perform(context)
    delay_mean_ms = LaunchConfiguration('delay_mean_ms').perform(context)
    delay_jitter_ms = LaunchConfiguration('delay_jitter_ms').perform(context)
    alpha_switch = LaunchConfiguration('alpha_switch').perform(context)
    beta_stale = LaunchConfiguration('beta_stale').perform(context)
    lambda_cost = LaunchConfiguration('lambda_cost').perform(context)
    enable_metrics = _to_bool(
        LaunchConfiguration('enable_metrics').perform(context)
    )
    metrics_output_dir = LaunchConfiguration('metrics_output_dir').perform(context)
    experiment_profile = LaunchConfiguration('experiment_profile').perform(context)
    use_fault_injection = _to_bool(
        LaunchConfiguration('use_fault_injection').perform(context)
    )

    namespaces = [f'{namespace_prefix}{i + 1}' for i in range(uav_count)]
    nodes = [
        Node(
            package='offboard_py',
            executable='task_board',
            name='task_board',
            parameters=[
                {
                    'publish_period_sec': 1.0,
                }
            ],
            output='screen',
        ),
    ]

    for namespace in namespaces:
        bid_publish_topic = 'auction/bid_raw' if use_fault_injection else 'auction/bid'
        nodes.append(
            Node(
                package='offboard_py',
                executable='offboard_control',
                namespace=namespace,
                name='offboard_control',
                output='screen',
            )
        )
        nodes.append(
            Node(
                package='offboard_py',
                executable='auction_agent',
                namespace=namespace,
                name='auction_agent',
                parameters=[
                    {
                        'agent_id': namespace,
                        'peer_namespaces': namespaces,
                        'bid_publish_topic': bid_publish_topic,
                        'peer_bid_topic_suffix': 'auction/bid',
                        'update_period_sec': float(base_update_period),
                        'alpha_switch': float(alpha_switch),
                        'beta_stale': float(beta_stale),
                        'lambda_cost': float(lambda_cost),
                    }
                ],
                output='screen',
            )
        )
        if use_fault_injection:
            nodes.append(
                Node(
                    package='offboard_py',
                    executable='network_faults',
                    namespace=namespace,
                    name='network_faults',
                    parameters=[
                        {
                            'input_topic': 'auction/bid_raw',
                            'output_topic': 'auction/bid',
                            'drop_probability': float(drop_probability),
                            'delay_mean_ms': float(delay_mean_ms),
                            'delay_jitter_ms': float(delay_jitter_ms),
                        }
                    ],
                    output='screen',
                )
            )
        if enable_metrics:
            nodes.append(
                Node(
                    package='offboard_py',
                    executable='metrics_recorder',
                    namespace=namespace,
                    name='metrics_recorder',
                    parameters=[
                        {
                            'profile_name': experiment_profile,
                            'output_dir': path.join(metrics_output_dir, namespace),
                            'source_topics': [
                                'auction/allocation',
                                'auction/bid',
                                'auction/local_state',
                            ],
                        }
                    ],
                    output='screen',
                )
            )

    return nodes


def generate_launch_description():
    """Generate the launch description for the auction SITL stack."""
    return LaunchDescription([
        DeclareLaunchArgument('uav_count', default_value='2'),
        DeclareLaunchArgument('namespace_prefix', default_value='px4_'),
        DeclareLaunchArgument('update_period_sec', default_value='0.2'),
        DeclareLaunchArgument('use_fault_injection', default_value='true'),
        DeclareLaunchArgument('drop_probability', default_value='0.0'),
        DeclareLaunchArgument('delay_mean_ms', default_value='0.0'),
        DeclareLaunchArgument('delay_jitter_ms', default_value='0.0'),
        DeclareLaunchArgument('alpha_switch', default_value='0.75'),
        DeclareLaunchArgument('beta_stale', default_value='1.0'),
        DeclareLaunchArgument('lambda_cost', default_value='1.0'),
        DeclareLaunchArgument('enable_metrics', default_value='false'),
        DeclareLaunchArgument(
            'metrics_output_dir',
            default_value='experiment_results/ad_hoc',
        ),
        DeclareLaunchArgument('experiment_profile', default_value='ad_hoc'),
        OpaqueFunction(function=_launch_setup),
    ])
