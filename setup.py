#!/usr/bin/env python3
# encoding=utf-8

import os

from appyratus.util import RealSetup

setup = RealSetup(
    path=os.path.abspath(os.path.dirname(__file__)),
    name='embryo',
    version='1.0',
    description='Embryo Renderer Scaffold Engine',
    author='Gigaquads',
    author_email='notdsk@gmail.com',
    url='https://github.com/gigaquads/embryo.git',
    classifiers=['python3', 'mit-license']
)
setup.run()
