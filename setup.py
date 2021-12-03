from collections.abc import Mapping
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import List

from setuptools import config, find_packages, setup


def installed_packages() -> List[str]:
    return [
        re.split('#egg=', re.split('==| @ ', package.decode())[0])[-1].lower()
        for package in subprocess.run(
            f'{sys.executable} -m pip freeze', shell=True, capture_output=True,
        ).stdout.splitlines()
    ]


try:
    if 'dunamai' not in installed_packages():
        subprocess.run(
            f'{sys.executable} -m pip install dunamai',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    from dunamai import Version

    version = Version.from_any_vcs().serialize()
except (ModuleNotFoundError, RuntimeError) as error:
    print(error)
    version = '0.0.0'

print(f'using version {version}')

metadata = config.read_configuration('setup.cfg')['metadata']

setup(
    name=metadata['name'],
    version=version,
    author=metadata['author'],
    author_email=metadata['author_email'],
    description=metadata['description'],
    long_description=metadata['long_description'],
    long_description_content_type='text/markdown',
    url=metadata['url'],
    packages=find_packages(),
    python_requires='>=3.6',
    setup_requires=['dunamai', 'setuptools>=41.2'],
    install_requires=['python-dateutil', 'pandas', 'pyproj>=2.6', 'shapely'],
    # test and development dependencies
    extras_require={
        'testing': ['FileLock', 'pytest', 'pytest-cov', 'pytest-socket', 'pytest-xdist',],
        'development': ['dunamai', 'flake8', 'isort', 'oitnb'],
        'documentation': ['dunamai', 'm2r2', 'sphinx', 'sphinx-rtd-theme'],
    },
)
