#!/bin/bash
#
# Copyright 2017 Catalyst IT Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $TOP_DIR/openrc admin admin

ZAQAR_DEVSTACK_DIR=$(cd $(dirname "$0")/.. && pwd)
source $ZAQAR_DEVSTACK_DIR/settings

set -o xtrace


function create {
    # TODO(flwang): Create queue, create subscriptions, post messages,
    # delete queue
    :
}

function verify {
    # TODO(flwang): Get queue, get messages, get subscriptions
    :
}

function verify_noapi {
    :
}

function destroy {
    # TODO(flwang): Purge queue, delete queue
    :
}

# Dispatcher
case $1 in
    "create")
        create
        ;;
    "verify")
        verify
        ;;
    "verify_noapi")
        verify_noapi
        ;;
    "destroy")
        destroy
        ;;
    "force_destroy")
        set +o errexit
        destroy
        ;;
esac

