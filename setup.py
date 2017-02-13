from setuptools import setup


setup(
    zip_safe=True,
    name='time-sync',
    version='0.1',
    author='adaml',
    author_email='adam.lavie@gmail.com',
    packages=[
        'time_sync',
        'time_sync_cli',
        'time_sync_cli.commands',
    ],
    license='LICENSE',
    description='Time-sync server/client application for electing and syncing'
                ' clients with a master client time.',
    entry_points={
        'console_scripts': [
            'tsc = time_sync_cli.cli:_tsc'
        ]
    },
    install_requires=[
        'celery==4.0.2',
        'docker-py==1.10.6',
        'pika==0.10.0',
        'redispy==3.0.0',
        'click>=6.7'
    ]

)
