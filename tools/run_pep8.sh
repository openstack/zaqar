#!/usr/bin/env bash

set -e
# This is used by run_tests.sh and tox.ini
python tools/hacking.py --doctest

# Until all these issues get fixed, ignore.
PEP8='python tools/hacking.py --ignore=N404'

EXCLUDE='--exclude=.venv,.git,.tox,dist,doc,*openstack/common*,*lib/python*'
EXCLUDE+=',./tools'
EXCLUDE+=',*egg,build'
${PEP8} ${EXCLUDE} .

! flake8 marconi --builtins=_,__MARCONI_SETUP__
