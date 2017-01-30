#!/bin/bash
#
#

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

# We need base DevStack functions for this
source $BASE_DEVSTACK_DIR/functions
source $BASE_DEVSTACK_DIR/stackrc # needed for status directory
source $BASE_DEVSTACK_DIR/lib/tls

# Keep track of the DevStack directory
ZAQAR_DEVSTACK_DIR=$(dirname "$0")/..
source $ZAQAR_DEVSTACK_DIR/settings
source $ZAQAR_DEVSTACK_DIR/plugin.sh

set -o xtrace

for serv in zaqar-websocket; do
    stop_process $serv
done

uwsgi --stop $ZAQAR_UWSGI_MASTER_PIDFILE