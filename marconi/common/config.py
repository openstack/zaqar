# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Decentralized configuration module.

A config variable `foo` is a read-only property accessible through

    cfg.foo

, where `cfg` is either a global configuration accessible through

    cfg = config.project('marconi').from_options(
        foo=("bar", "usage"),
        ...)

, or a local configuration associated with a namespace

    cfg = config.namespace('drivers:transport:wsgi').from_options(
        port=80,
        ...)

The `from_options` call accepts a list of option definition, where each
option is represented as a keyword argument, in the form of either
`name=default` or `name=(default, description)`, where `name` is the
name of the option in a valid Python identifier, and `default` is the
default value of that option.

Configurations can be read from an INI file, where the global options
are under the `[DEFAULT]` section, and the local options are under the
sections named by their associated namespaces.

To load the configurations from a file:

    cfg_handle = config.project('marconi')
    cfg_handle.load(filename="/path/to/example.conf")

A call to `.load` without a filename looks up for the default ones:

    ~/.marconi/marconi.conf
    /etc/marconi/marconi.conf

Global config variables, if any, can also be read from the command line
arguments:

    cfg_handle.load(filename="example.conf", args=sys.argv[1:])
"""

from oslo.config import cfg


def _init():
    """Enclose an API specific config object."""

    class ConfigProxy(object):
        """Prototype of the opaque config variable accessors."""
        pass

    class Obj(dict):
        __getattr__ = dict.__getitem__
        __setattr__ = dict.__setitem__

    conf = cfg.ConfigOpts()

    def namespace(name, title=None):
        """
        Create a config namespace.

        :param name: the section name appears in the .ini file
        :param title: an optional description
        :returns: the option object for the namespace
        """

        grp = cfg.OptGroup(name, title)
        conf.register_group(grp)

        def from_options(**opts):
            """
            Define options under the associated namespace.

            :returns: ConfigProxy of the associated namespace
            """

            for k, v in opts.items():
                conf.register_opt(_make_opt(k, v), group=grp)

            def from_class(cls):
                grant_access_to_class(conf[grp.name], cls)
                return cls

            return from_class(opaque_type_of(ConfigProxy, grp.name))()

        return Obj(from_options=from_options)

    def project(name=None):
        """
        Access the global namespace.

        :param name: the name of the project
        :returns: a global option object
        """

        def from_options(**opts):
            """
            Define options under the global namespace.

            :returns: ConfigProxy of the global namespace
            """

            for k, v in opts.items():
                conf.register_cli_opt(_make_opt(k, v))

            def from_class(cls):
                grant_access_to_class(conf, cls)
                return cls

            return from_class(opaque_type_of(ConfigProxy, name))()

        def load(filename=None, args=None):
            """Load the configurations from a config file.

            If the file name is not supplied, look for

                ~/.%project/%project.conf

                and

                /etc/%project/%project.conf

            :param filename: the name of an alternative config file
            :param args: command line arguments
            """

            args = [] if args is None else args

            if filename is None:
                conf(args=args, project=name, prog=name)
            else:
                conf(args=args, default_config_files=[filename])

        return Obj(from_options=from_options, load=load)

    def opaque_type_of(base, postfix):
        return type('%s of %s' % (base.__name__, postfix), (base,), {})

    def grant_access_to_class(pairs, cls):
        for k in pairs:
            # A closure is needed for each %k to let
            # different properties access different %k.
            def let(k=k):
                setattr(cls, k, property(lambda obj: pairs[k]))
            let()

    return namespace, project


namespace, project = _init()


def _make_opt(name, default):
    """
    Create an oslo.config option with the type deduce from the %default
    value of an option %name.

    A default value of None is deduced to Opt.  MultiStrOpt is not supported.

    :param name: the name of the option in a valid Python identifier
    :param default: the default value of the option, or (default, description)
    :raises: cfg.Error if the type can not be deduced.
    """

    deduction = {
        str: cfg.StrOpt,
        bool: cfg.BoolOpt,
        int: cfg.IntOpt,
        long: cfg.IntOpt,
        float: cfg.FloatOpt,
        list: cfg.ListOpt,
    }

    if type(default) is tuple:
        default, help = default
    else:
        help = None

    if default is None:
        return cfg.Opt(name, help=help)

    try:
        return deduction[type(default)](name, help=help, default=default)
    except KeyError:
        raise cfg.Error("unrecognized option type")
