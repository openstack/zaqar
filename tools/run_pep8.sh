#!/usr/bin/env bash

set -e

PEP8='python tools/hacking.py --ignore=N404'
FLAKE8='flake8 --builtins=_,__MARCONI_SETUP__'

EXCLUDE='--exclude=.venv,.git,.tox,dist,doc,*openstack/common*,*lib/python*'
EXCLUDE+=',./tools'
EXCLUDE+=',*egg,build'

if [ $1 = pep8 ]
then
    ${PEP8} ${EXCLUDE} .
else
    ${FLAKE8} ${EXCLUDE}
fi