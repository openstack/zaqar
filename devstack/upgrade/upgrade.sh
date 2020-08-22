#!/usr/bin/env bash

# ``upgrade-zaqar``

echo "*********************************************************************"
echo "Begin $0"
echo "*********************************************************************"

# Clean up any resources that may be in use
cleanup() {
    set +o errexit

    echo "*********************************************************************"
    echo "ERROR: Abort $0"
    echo "*********************************************************************"

    # Kill ourselves to signal any calling process
    trap 2; kill -2 $$
}

trap cleanup SIGHUP SIGINT SIGTERM

# Keep track of the grenade directory
RUN_DIR=$(cd $(dirname "$0") && pwd)

# Source params
source $GRENADE_DIR/grenaderc

source $TOP_DIR/openrc admin admin

# Import common functions
source $GRENADE_DIR/functions

# This script exits on an error so that errors don't compound and you see
# only the first error that occurred.
set -o errexit

if grep -q '_store *= *mongodb' /etc/zaqar/zaqar.conf; then
    # mongo-tools is the name of the package which includes mongodump on
    # basically all distributions (Ubuntu, Debian, Fedora, CentOS and
    # openSUSE).
    install_package mongo-tools
fi

if grep -q 'management_store *= *mongodb' /etc/zaqar/zaqar.conf; then
    mongodump --db zaqar_mgmt --out $SAVE_DIR/zaqar-mongodb-mgmt-dump.$BASE_RELEASE
fi

if grep -q 'message_store *= *mongodb' /etc/zaqar/zaqar.conf; then
    mongodump --db zaqar --out $SAVE_DIR/zaqar-mongodb-message-dump.$BASE_RELEASE
fi

if grep -q 'message_store *= *redis' /etc/zaqar/zaqar.conf; then
    redis-cli save
    sudo cp /var/lib/redis/dump.rdb $SAVE_DIR/zaqar-redis-message-dump-$BASE_RELEASE.rdb
fi

# Upgrade Zaqar
# =============

# Duplicate some setup bits from target DevStack
source $TARGET_DEVSTACK_DIR/stackrc
source $TARGET_DEVSTACK_DIR/lib/tls

# Keep track of the DevStack directory
ZAQAR_DEVSTACK_DIR=$(dirname "$0")/..
source $ZAQAR_DEVSTACK_DIR/settings
source $ZAQAR_DEVSTACK_DIR/plugin.sh

# Print the commands being run so that we can see the command that triggers
# an error.  It is also useful for following allowing as the install occurs.
set -o xtrace

function wait_for_keystone {
    local www_authenticate_uri=http://${ZAQAR_SERVICE_HOST}/identity
    if ! wait_for_service $SERVICE_TIMEOUT ${www_authenticate_uri}/v$IDENTITY_API_VERSION/; then
        die $LINENO "keystone did not start"
    fi
}

# Save current config files for posterity
[[ -d $SAVE_DIR/etc.zaqar ]] || cp -pr $ZAQAR_CONF_DIR $SAVE_DIR/etc.zaqar

stack_install_service zaqar

if grep -q 'management_store *= *sqlalchemy' /etc/zaqar/zaqar.conf; then
    zaqar-sql-db-manage --config-file $ZAQAR_CONF upgrade head || die $LINENO "DB sync error"
fi

# calls upgrade-zaqar for specific release
upgrade_project zaqar $RUN_DIR $BASE_DEVSTACK_BRANCH $TARGET_DEVSTACK_BRANCH

wait_for_keystone
start_zaqar


# Don't succeed unless the services come up
ensure_services_started zaqar-server

if grep -q 'management_store *= *mongodb' /etc/zaqar/zaqar.conf; then
    mongodump --db zaqar_mgmt --out $SAVE_DIR/zaqar-mongodb-mgmt-dump.$TARGET_RELEASE
fi

if grep -q 'message_store *= *mongodb' /etc/zaqar/zaqar.conf; then
    mongodump --db zaqar --out $SAVE_DIR/zaqar-mongodb-message-dump.$TARGET_RELEASE
fi

if grep -q 'message_store *= *redis' /etc/zaqar/zaqar.conf; then
    redis-cli save
    sudo cp /var/lib/redis/dump.rdb $SAVE_DIR/zaqar-redis-message-dump-$TARGET_RELEASE.rdb
fi

set +o xtrace
echo "*********************************************************************"
echo "SUCCESS: End $0"
echo "*********************************************************************"
