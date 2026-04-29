from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'rtabmap_ntust'

resource_files = []
for root, dirs, files in os.walk('resource'):
    for f in files:
        if f == package_name:
            # 跳過 ROS 2 marker 檔
            continue
        dest_dir = os.path.join(
            'share', package_name, 'resource',
            os.path.relpath(root, 'resource')
        )
        resource_files.append((dest_dir, [os.path.join(root, f)]))

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    install_requires=['setuptools'],

    data_files=[
    ('share/ament_index/resource_index/packages',
        ['resource/' + package_name]),
    ] + resource_files + [
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'), sorted(glob('launch/*.py'))),
    (os.path.join('share', package_name, 'worlds'), sorted(glob('worlds/*.wbt'))),
    ],

    zip_safe=True,
    maintainer='danny',
    maintainer_email='ddak3914@mail.com',
    description='rtabmap_ntust package for Webots simulation',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'buildings_marker = rtabmap_webot.buildings_marker:main',
        ],
    },
)
