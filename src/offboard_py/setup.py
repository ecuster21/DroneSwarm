from glob import glob

from setuptools import find_packages, setup

package_name = 'offboard_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jie',
    maintainer_email='jie@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'offboard_control = offboard_py.offboard_control:main',
            'auction_agent = offboard_py.auction_agent:main',
            'task_board = offboard_py.task_board:main',
            'network_faults = offboard_py.network_faults:main',
            'experiment_logger = offboard_py.experiment_logger:main',
            'metrics_recorder = offboard_py.metrics_recorder:main',
            'experiment_summarizer = offboard_py.experiment_summary:main',
            'experiment_reporter = offboard_py.experiment_report:main',
            'experiment_batch_runner = offboard_py.experiment_batch:main',
            'experiment_study_reporter = offboard_py.experiment_study:main',
            'experiment_paper_assets = offboard_py.paper_assets:main',
        ],
    },
)
