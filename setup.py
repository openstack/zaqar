#!/usr/bin/env python
# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import setuptools

import __builtin__
__builtin__.__MARCONI_SETUP__ = True
from marconi.openstack.common import setup as common_setup

requires = common_setup.parse_requirements()
dependency_links = common_setup.parse_dependency_links()

setuptools.setup(
    name='marconi',
    version=common_setup.get_version('marconi'),
    description='Message Bus for OpenStack',
    license="Apache License (2.0)",
    author='Kurt Griffiths',
    author_email='kurt.griffiths@rackspace.com',
    url='https://launchpad.net/marconi',
    packages=setuptools.find_packages(exclude=['bin']),
    include_package_data=True,
    test_suite='nose.collector',
    install_requires=requires,
    dependency_links=dependency_links,
    cmdclass=common_setup.get_cmdclass(),
    entry_points={
        'console_scripts':
            ['marconi-server = marconi.bin.server:run']
    }
)
