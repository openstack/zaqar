# Copyright (c) 2013 Rackspace Hosting, Inc.
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

"""utils: general-purpose utilities."""

from oslo_config import cfg
import six


def fields(d, names, pred=lambda x: True,
           key_transform=lambda x: x, value_transform=lambda x: x):
    """Returns the entries in this dictionary with keys appearing in names.

    :type d: dict
    :type names: [a]
    :param pred: a filter that is applied to the values of the dictionary.
    :type pred: (a -> bool)
    :param key_transform: a transform to apply to the key before returning it
    :type key_transform: a -> a
    :param value_transform: a transform to apply to the value before
        returning it
    :type value_transform: a -> a
    :rtype: dict
    """

    return dict((key_transform(k), value_transform(v))
                for k, v in d.items()
                if k in names and pred(v))


_pytype_to_cfgtype = {
    six.text_type: cfg.StrOpt,
    str: cfg.StrOpt,
    int: cfg.IntOpt,
    bool: cfg.BoolOpt,
    float: cfg.FloatOpt,
    list: cfg.ListOpt,
    dict: cfg.DictOpt
}


def dict_to_conf(options):
    """Converts a python dictionary to a list of oslo_config.cfg.Opt

    :param options: The python dictionary to convert
    :type options: dict
    :returns: a list of options compatible with oslo_config
    :rtype: [oslo_config.cfg.Opt]
    """

    opts = []

    for k, v in options.items():
        opt_type = _pytype_to_cfgtype[type(v)]
        opts.append(opt_type(name=k, default=v))

    return opts
