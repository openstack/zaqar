#!/bin/bash
#
# lib/zaqar
# Install and start **Zaqar** service

# To enable a minimal set of Zaqar services, add the following to localrc:
#
#     enable_service zaqar-websocket zaqar-wsgi
#
# Dependencies:
# - functions
# - OS_AUTH_URL for auth in api
# - DEST set to the destination directory
# - SERVICE_PASSWORD, SERVICE_TENANT_NAME for auth in api
# - STACK_USER service user

# stack.sh
# ---------
# install_zaqar
# install_zaqarui
# configure_zaqar
# init_zaqar
# start_zaqar
# stop_zaqar
# cleanup_zaqar
# cleanup_zaqar_mongodb

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set +o xtrace

# Functions
# ---------

# Test if any Zaqar services are enabled
# is_zaqar_enabled
function is_zaqar_enabled {
    [[ ,${ENABLED_SERVICES} =~ ,"zaqar" ]] && return 0
    return 1
}

# cleanup_zaqar() - Cleans up general things from previous
# runs and storage specific left overs.
function cleanup_zaqar {
    if [ "$ZAQAR_BACKEND" = 'mongodb' ] ; then
        cleanup_zaqar_mongodb
    fi
    remove_uwsgi_config "$ZAQAR_UWSGI_CONF" "zaqar"
}

# cleanup_zaqar_mongodb() - Remove residual data files, anything left over from previous
# runs that a clean run would need to clean up
# After mongodb 6.0, the mongo shell has been remove, now using mongosh.
function cleanup_zaqar_mongodb {
    if ! timeout $SERVICE_TIMEOUT sh -c "while ! mongosh zaqar --eval 'db.dropDatabase();'; do sleep 1; done"; then
        die $LINENO "Mongo DB did not start"
    else
        mongo_version=$(mongosh zaqar --eval 'db.version();')
        required_mongo_version='6.0'
        if [[ $mongo_version < $required_mongo_version ]]; then
            die $LINENO "Zaqar needs Mongo DB version >= 6.0 to run."
        fi
    fi
}

# configure_zaqarclient() - Set config files, create data dirs, etc
function configure_zaqarclient {
    setup_develop $ZAQARCLIENT_DIR
}

# configure_zaqar() - Set config files, create data dirs, etc
function configure_zaqar {
    setup_develop $ZAQAR_DIR

    [ ! -d $ZAQAR_CONF_DIR ] && sudo mkdir -m 755 -p $ZAQAR_CONF_DIR
    sudo chown $USER $ZAQAR_CONF_DIR

    [ ! -d $ZAQAR_API_LOG_DIR ] && sudo mkdir -m 755 -p $ZAQAR_API_LOG_DIR
    sudo chown $USER $ZAQAR_API_LOG_DIR

    iniset $ZAQAR_CONF DEFAULT debug True
    iniset $ZAQAR_CONF DEFAULT unreliable True
    iniset $ZAQAR_CONF DEFAULT admin_mode True
    iniset $ZAQAR_CONF DEFAULT enable_deprecated_api_versions 1,1.1
    iniset $ZAQAR_CONF signed_url secret_key notreallysecret

    if is_service_enabled key; then
        iniset $ZAQAR_CONF DEFAULT auth_strategy keystone
    fi

    iniset $ZAQAR_CONF storage message_pipeline zaqar.notification.notifier

    # Enable pooling by default for now
    iniset $ZAQAR_CONF DEFAULT admin_mode True
    iniset $ZAQAR_CONF 'drivers:transport:websocket' bind $(ipv6_unquote $ZAQAR_SERVICE_HOST)
    iniset $ZAQAR_CONF 'drivers:transport:websocket' port $ZAQAR_WEBSOCKET_PORT
    iniset $ZAQAR_CONF drivers transport websocket

    configure_keystone_authtoken_middleware $ZAQAR_CONF zaqar

    iniset $ZAQAR_CONF trustee auth_type password
    iniset $ZAQAR_CONF trustee auth_url $KEYSTONE_AUTH_URI
    iniset $ZAQAR_CONF trustee username $ZAQAR_TRUSTEE_USER
    iniset $ZAQAR_CONF trustee password $ZAQAR_TRUSTEE_PASSWORD
    iniset $ZAQAR_CONF trustee user_domain_id $ZAQAR_TRUSTEE_DOMAIN

    iniset $ZAQAR_CONF DEFAULT pooling True
    iniset $ZAQAR_CONF 'pooling:catalog' enable_virtual_pool True

    if [ "$ZAQAR_BACKEND" = 'mongodb' ] ; then
        iniset $ZAQAR_CONF  drivers message_store mongodb
        iniset $ZAQAR_CONF 'drivers:message_store:mongodb' uri mongodb://localhost:27017/zaqar
        iniset $ZAQAR_CONF 'drivers:message_store:mongodb' database zaqar

        iniset $ZAQAR_CONF  drivers management_store mongodb
        iniset $ZAQAR_CONF 'drivers:management_store:mongodb' uri mongodb://localhost:27017/zaqar_mgmt
        iniset $ZAQAR_CONF 'drivers:management_store:mongodb' database zaqar_mgmt
        configure_mongodb
    elif [ "$ZAQAR_BACKEND" = 'redis' ] ; then
        recreate_database zaqar
        iniset $ZAQAR_CONF  drivers management_store sqlalchemy
        iniset $ZAQAR_CONF 'drivers:management_store:sqlalchemy' uri `database_connection_url zaqar`
        iniset $ZAQAR_CONF 'drivers:management_store:sqlalchemy' database zaqar_mgmt

        $ZAQAR_BIN_DIR/zaqar-sql-db-manage --config-file $ZAQAR_CONF upgrade head

        iniset $ZAQAR_CONF  drivers message_store redis
        iniset $ZAQAR_CONF 'drivers:message_store:redis' uri redis://localhost:6379
        iniset $ZAQAR_CONF 'drivers:message_store:redis' database zaqar
        configure_redis
    elif [ "$ZAQAR_BACKEND" = 'swift' ] ; then
        recreate_database zaqar
        iniset $ZAQAR_CONF  drivers management_store sqlalchemy
        iniset $ZAQAR_CONF 'drivers:management_store:sqlalchemy' uri `database_connection_url zaqar`
        iniset $ZAQAR_CONF 'drivers:management_store:sqlalchemy' database zaqar_mgmt

        $ZAQAR_BIN_DIR/zaqar-sql-db-manage --config-file $ZAQAR_CONF upgrade head

        iniset $ZAQAR_CONF  drivers message_store swift
        iniset $ZAQAR_CONF 'drivers:message_store:swift' auth_url $KEYSTONE_AUTH_URI
        iniset $ZAQAR_CONF 'drivers:message_store:swift' uri swift://zaqar:$SERVICE_PASSWORD@/service
    fi

    if is_service_enabled qpid || [ -n "$RABBIT_HOST" ] && [ -n "$RABBIT_PASSWORD" ]; then
        iniset $ZAQAR_CONF DEFAULT notification_driver messaging
        iniset $ZAQAR_CONF DEFAULT control_exchange zaqar
    fi
    iniset_rpc_backend zaqar $ZAQAR_CONF DEFAULT

    write_uwsgi_config "$ZAQAR_UWSGI_CONF" "$ZAQAR_UWSGI" "/messaging" "" "zaqar"
}

function configure_redis {
    if is_ubuntu; then
        install_package redis-server
        pip_install redis
    elif is_fedora; then
        install_package redis
        pip_install redis
    else
        exit_distro_not_supported "redis installation"
    fi
}

function configure_mongodb {
    # Set nssize to 2GB. This increases the number of namespaces supported
    # per database.
    pip_install pymongo
    if is_ubuntu; then
        # NOTE: To fix the mongodb's issue in ubuntu 22.04/24.04 LTS
        ubuntu_version=$(source /etc/os-release ; echo $VERSION_ID)
        if [[ $ubuntu_version == '24.04' ]]; then
            sudo mkdir /etc/apt/sources.list.d
            wget -qO - https://www.mongodb.org/static/pgp/server-8.0.asc | sudo apt-key add -
            echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
            sudo apt update
            install_package mongodb-org
            restart_service mongod
            sudo systemctl status mongod
        elif [[ $ubuntu_version == '22.04' ]]; then
            wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
            echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
            sudo apt update
            install_package mongodb-org
            restart_service mongod
            sudo systemctl status mongod
        else
            install_package mongodb-server
            restart_service mongodb
        fi
    elif is_fedora; then
        fedora_version=$(source /etc/os-release ; echo $VERSION_ID)
        if [[ $fedora_version == '9' ]]; then
            cat > /etc/yum.repos.d/mongodb-org-6.0.repo << __EOF__
[mongodb-org-6.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/8/mongodb-org/6.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-6.0.asc
__EOF__
            install_package mongodb-org
            restart_service mongod
        else
            install_package mongodb
            install_package mongodb-server
            restart_service mongod
        fi
    fi
}

# init_zaqar() - Initialize etc.
function init_zaqar {
    # Nothing to do
    :
}

# install_zaqar() - Collect source and prepare
function install_zaqar {
    setup_develop $ZAQAR_DIR

    if is_service_enabled horizon; then
        install_zaqarui
    fi
    pip_install uwsgi
}

function install_zaqarui {
    git_clone $ZAQARUI_REPO $ZAQARUI_DIR $ZAQARUI_BRANCH
    # NOTE(flwang): Workaround for devstack bug: 1540328
    # where devstack install 'test-requirements' but should not do it
    # for zaqar-ui project as it installs Horizon from url.
    # Remove following two 'mv' commands when mentioned bug is fixed.
    mv $ZAQARUI_DIR/test-requirements.txt $ZAQARUI_DIR/_test-requirements.txt
    setup_develop $ZAQARUI_DIR
    mv $ZAQARUI_DIR/_test-requirements.txt $ZAQARUI_DIR/test-requirements.txt
    cp -a $ZAQARUI_DIR/zaqar_ui/enabled/* $HORIZON_DIR/openstack_dashboard/local/enabled/
    if [ -d $ZAQARUI_DIR/zaqar-ui/locale ]; then
        (cd $ZAQARUI_DIR/zaqar-ui; DJANGO_SETTINGS_MODULE=openstack_dashboard.settings ../manage.py compilemessages)
    fi
}

# install_zaqarclient() - Collect source and prepare
function install_zaqarclient {
    git_clone $ZAQARCLIENT_REPO $ZAQARCLIENT_DIR $ZAQARCLIENT_BRANCH
    # NOTE(flaper87): Ideally, this should be developed, but apparently
    # there's a bug in devstack that skips test-requirements when using
    # setup_develop
    setup_install $ZAQARCLIENT_DIR
}

# start_zaqar() - Start running processes, including screen
function start_zaqar {
    run_process zaqar-wsgi "$ZAQAR_BIN_DIR/uwsgi --ini $ZAQAR_UWSGI_CONF"
    run_process zaqar-websocket "$ZAQAR_BIN_DIR/zaqar-server --config-file $ZAQAR_CONF"

    echo "Waiting for Zaqar to start..."
    local www_authenticate_uri=http://${ZAQAR_SERVICE_HOST}/identity
    local ping_url=$ZAQAR_SERVICE_PROTOCOL://$ZAQAR_SERVICE_HOST/messaging/v2/ping
    token=$(openstack token issue -c id -f value --os-auth-url ${www_authenticate_uri})
    if ! timeout $SERVICE_TIMEOUT sh -c "while ! wget --no-proxy -q --header=\"Client-ID:$(uuidgen)\" --header=\"X-Auth-Token:$token\" -O- $ping_url; do sleep 1; done"; then
        die $LINENO "Zaqar did not start"
    fi
}

# stop_zaqar() - Stop running processes
function stop_zaqar {
    local serv
    # Kill the zaqar screen windows
    for serv in zaqar-wsgi zaqar-websocket; do
        stop_process serv
    done
}

function create_zaqar_accounts {
    create_service_user "zaqar"

    if [[ "$KEYSTONE_IDENTITY_BACKEND" = 'sql' ]]; then

        get_or_create_service "zaqar" "messaging" "Zaqar Service"
        get_or_create_endpoint "messaging" \
            "$REGION_NAME" \
            "$ZAQAR_SERVICE_PROTOCOL://$ZAQAR_SERVICE_HOST/messaging"

        get_or_create_service "zaqar-websocket" \
            "messaging-websocket" "Zaqar Websocket Service"
        get_or_create_endpoint "messaging-websocket" \
            "$REGION_NAME" \
            "$ZAQAR_SERVICE_PROTOCOL://$ZAQAR_SERVICE_HOST:$ZAQAR_WEBSOCKET_PORT"
    fi

    if [ "$ZAQAR_BACKEND" = 'swift' ] ; then
        get_or_add_user_project_role ResellerAdmin zaqar service
    fi
}

if is_service_enabled zaqar-websocket || is_service_enabled zaqar-wsgi; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Zaqar"
        install_zaqarclient
        install_zaqar
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Zaqar"
        configure_zaqar
        configure_zaqarclient

        if is_service_enabled key; then
           create_zaqar_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing Zaqar"
        init_zaqar
        start_zaqar
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_zaqar
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_zaqar
    fi
fi

# Restore xtrace
$XTRACE

# Local variables:
# mode: shell-script
# End:
