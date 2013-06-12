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

import csv

from marconi.tests.system.common import config
from marconi.tests.system.common import functionlib


cfg = config.Config()


def get_data():
    """Gets Test data from a csv file."""
    data = []
    with open('marconi/tests/system/messages/test_data.csv', 'rb') as datafile:
        test_data = csv.DictReader(datafile, delimiter='|')
        for row in test_data:
            data.append(row)

    for row in data:
        row['header'] = functionlib.get_headers(row['header'])
        row['url'] = row['url'].replace("<BASE_URL>", cfg.base_url)

    return data


API_TEST_DATA = get_data()
