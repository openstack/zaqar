#!/bin/bash
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

# This script is executed inside gate_hook function in devstack gate.

ENABLED_SERVICES="mysql,key,tempest,zaqar-websocket,zaqar-wsgi"

export DEVSTACK_GATE_ZAQAR=1
export DEVSTACK_GATE_INSTALL_TESTONLY=1
export DEVSTACK_GATE_NO_SERVICES=1
export DEVSTACK_GATE_TEMPEST=0
export DEVSTACK_GATE_EXERCISES=0
export DEVSTACK_GATE_TIMEOUT=90
export KEEP_LOCALRC=1

export DEVSTACK_GATE_ZAQAR_TEST_SUITE=$1
# NOTE(flaper87): Backwards compatibility until `project-config`'s
# patch lands.
export DEVSTACK_GATE_ZAQAR_BACKEND=${2:-$DEVSTACK_GATE_ZAQAR_TEST_SUITE}
export DEVSTACK_LOCAL_CONFIG+=$"
export ZAQAR_BACKEND=$DEVSTACK_GATE_ZAQAR_BACKEND"
export ENABLED_SERVICES

function run_devstack_gate() {
    $BASE/new/devstack-gate/devstack-vm-gate.sh
}

function run_tempest_tests() {
    export DEVSTACK_GATE_TEMPEST=1
    run_devstack_gate
}

function run_zaqarclient_tests() {
    run_devstack_gate
    cd $BASE/new/python-zaqarclient

    source $BASE/new/devstack/openrc
    cat /etc/mongodb.conf
    ZAQARCLIENT_AUTH_FUNCTIONAL=1 nosetests tests.functional
}

case "$DEVSTACK_GATE_ZAQAR_TEST_SUITE" in
    tempest)
	run_tempest_tests
	;;
    zaqarclient)
	run_zaqarclient_tests
	;;
    *)
	# NOTE(flaper87): Eventually, this will error
	run_zaqarclient_tests
	;;
esac

