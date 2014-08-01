# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import pbr.packaging

import zaqar
from zaqar import tests as testing


class TestVersion(testing.TestBase):

    def test_correct_hash(self):
        version = pbr.packaging._get_version_from_git('201X.X')
        if version is None:
            self.skipTest('Unable to obtain version from git')

        pre, sep, commit = version.rpartition('.')

        if not commit or not commit.startswith('g'):
            self.skipTest('The git version string does not contain a hash')

        sha_abbrev = commit[1:]
        self.assertTrue(zaqar.version.verify_sha(sha_abbrev))

        sha_abbrev_bad = 'x' + sha_abbrev[1:]
        self.assertFalse(zaqar.version.verify_sha(sha_abbrev_bad))
