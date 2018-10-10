#!/usr/bin/env python3
# encoding=utf-8

import os
from setuptools import setup

setup(
    name='embryo',
    version='0b1',
    description='Embryo Renderer Scaffold Engine',
    author='Gigaquads',
    author_email='notdsk@gmail.com',
    url='https://github.com/gigaquads/embryo.git',
    dependency_links=[
        'https://github.com/gigaquads/appyratus/tarball/master#egg=appyratus'
    ]
    #classifiers=['python3', 'mit-license']
)
