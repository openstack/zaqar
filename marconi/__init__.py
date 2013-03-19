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

# Import guard.  No module level import during the setup procedure.
try:
    __MARCONI_SETUP__  # NOQA
except NameError:
    import gettext
    gettext.install("marconi", unicode=1)
    from marconi.bootstrap import Bootstrap  # NOQA
else:
    import sys as _sys
    _sys.stderr.write('Running from marconi source directory.\n')
    del _sys

import marconi.version

__version__ = marconi.version.version_info.deferred_version_string()
