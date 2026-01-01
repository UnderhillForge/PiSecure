#!/usr/bin/env python3
"""
Setup script for PiSecure - Decentralized Security Framework for Raspberry Pi
"""

from setuptools import setup, find_packages
import os

# Read version from __init__.py
def get_version():
    with open(os.path.join('pisecure', '__init__.py'), 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return '0.1.0'

# Read README for long description
def get_long_description():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

setup(
    name='pisecure',
    version=get_version(),
    description='Decentralized Security Framework for Raspberry Pi',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='J Stekervetz',
    author_email='mr_underhill@icloud.com',
    url='https://github.com/UnderhillForge/PiSecure',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'cryptography>=41.0.0',
        'PyNaCl>=1.5.0',
        'requests>=2.31.0',
        'click>=8.1.0',
        'rich>=13.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
        ],
        'hardware': [
            'RPi.GPIO>=0.7.0',
            'gpiozero>=2.0',
        ],
        'ipfs': [
            'ipfshttpclient>=0.8.0',
        ],
        'tpm': [
            'tpm2-pytss>=1.2.0',
        ],
        'full': [
            'ipfshttpclient>=0.8.0',
            'RPi.GPIO>=0.7.0',
            'gpiozero>=2.0',
            'tpm2-pytss>=1.2.0',
            'asyncio-mqtt>=0.13.0',
            'jsonschema>=4.17.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'pisecure=launch_pisecure:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Security',
        'Topic :: Security :: Cryptography',
        'Topic :: System :: Hardware',
        'Topic :: Internet :: WWW/HTTP',
    ],
    keywords='raspberry-pi blockchain security iot cryptography hardware-verification',
    python_requires='>=3.7',
    project_urls={
        'Bug Reports': 'https://github.com/UnderhillForge/PiSecure/issues',
        'Source': 'https://github.com/UnderhillForge/PiSecure',
        'Documentation': 'https://pisecure.readthedocs.io/',
    },
)