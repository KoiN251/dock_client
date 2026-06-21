from setuptools import setup

package_name = 'uav_dock_client'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ctuav',
    maintainer_email='ctuav@example.com',
    description='CTUAV UAV Dock client.',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'uav_dock_client_node = uav_dock_client.uav_dock_client_node:main',
        ],
    },
)
