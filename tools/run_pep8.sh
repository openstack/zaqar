#!/bin/bash

set -e
# This is used by run_tests.sh and tox.ini
python tools/hacking.py --doctest

# Until all these issues get fixed, ignore.
PEP8='python tools/hacking.py --ignore=E12,E711,E721,E712,N303,N403,N404'

EXCLUDE='--exclude=.venv,.git,.tox,dist,doc,*openstack/common*,*lib/python*'
EXCLUDE+=',*egg,build'
${PEP8} ${EXCLUDE} .

${PEP8} --filename=marconi* bin

! pyflakes marconi/ | grep "imported but unused\|redefinition of function" | grep -v "__init__.py"
