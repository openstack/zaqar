# Copyright (c) 2013 OpenStack Foundation
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

import pbr.version


version_info = pbr.version.VersionInfo('zaqar')
version_string = version_info.version_string


def verify_sha(expected):
    """Verifies the commit hash for an interim Zaqar build.

    This function may be used to verify that the version of the zaqar
    package, as imported from an environment's site-packages, is the
    expected build. This allows continuous integration scripts to
    detect out-of-date installations of the package.

    Note that this function will ALWAYS return False for Zaqar packages
    that were not installed from git.

    :param expected: The expected commit object name. May be either a full
        or abbreviated SHA hash. If abbreviated, at least 7 digits are
        required.
    :returns: True if the package's version string contains a hash, and
        that hash matches `expected`. Otherwise returns False.
    """

    # NOTE(kgriffs): Require 7 digits to avoid false positives. In practice,
    # Git's abbreviated commit oject names will always include at least
    # 7 digits.
    assert len(expected) >= 7

    # NOTE(kgriffs): Git usually abbreviates hashed to 7 digits, but also
    # check 8 digits in case git decides just 7 is ambiguous. Accordingly,
    # try the longer one first since it is more specific than the other.
    for abbreviated in (expected[:8], expected[:7]):
        if ('.g' + abbreviated) in version_info.release_string():
            return True

    return False
