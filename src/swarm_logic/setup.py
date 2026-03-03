from setuptools import find_packages, setup


package_name = 'swarm_logic'


setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jie',
    maintainer_email='jie@todo.todo',
    description='Centralized swarm reconnaissance mission controller.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            (
                'swarm_recon_controller = '
                'swarm_logic.swarm_recon_controller:main'
            ),
        ],
    },
)
