from setuptools import setup, find_packages

import os


def readlines(filename):
    if not os.path.exists(filename):
        return []
    with open(filename) as f:
        return f.readlines()


setup(
    name="hrsync",
    version="0.0.1",

    package_dir={'': '.'},
    packages=find_packages(),
    include_package_data=True,
    install_requires=readlines('requirements.txt')
)
