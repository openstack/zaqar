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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import io

import falcon
import json
import testtools

from marconi.transport.wsgi import utils


class TestWSGIutils(testtools.TestCase):

    def test_get_checked_field_missing(self):
        doc = {}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack', int)

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 42, int)

        doc = {'openstac': 10}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack', int)

    def test_get_checked_field_bad_type(self):
        doc = {'openstack': '10'}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack', int)

        doc = {'openstack': 10, 'openstack-mq': 'test'}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack', str)

        doc = {'openstack': '[1, 2]'}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack', list)

    def test_get_checked_field(self):
        doc = {'hello': 'world', 'teh answer': 42, 'question': []}

        value = utils.get_checked_field(doc, 'hello', str)
        self.assertEquals(value, 'world')

        value = utils.get_checked_field(doc, 'teh answer', int)
        self.assertEquals(value, 42)

        value = utils.get_checked_field(doc, 'question', list)
        self.assertEquals(value, [])

    def test_filter_missing(self):
        doc = {'body': {'event': 'start_backup'}}
        spec = (('tag', dict),)
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.filter, doc, spec)

    def test_filter_bad_type(self):
        doc = {'ttl': '300', 'bogus': 'yogabbagabba'}
        spec = [('ttl', int)]
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.filter, doc, spec)

    def test_filter(self):
        doc = {'body': {'event': 'start_backup'}}

        def spec():
            yield ('body', dict)

        filtered = utils.filter(doc, spec())
        self.assertEqual(filtered, doc)

        doc = {'ttl': 300, 'bogus': 'yogabbagabba'}
        spec = [('ttl', int)]
        filtered = utils.filter(doc, spec)
        self.assertEqual(filtered, {'ttl': 300})

        doc = {'body': {'event': 'start_backup'}, 'ttl': 300}
        spec = (('body', dict), ('ttl', int))
        filtered = utils.filter(doc, spec)
        self.assertEqual(filtered, doc)

    def test_filter_star(self):
        doc = {'ttl': 300, 'body': {'event': 'start_backup'}}

        spec = [('body', '*'), ('ttl', '*')]
        filtered = utils.filter(doc, spec)

        self.assertEqual(filtered, doc)

    def test_filter_stream_expect_obj(self):
        obj = {u'body': {'event': 'start_backup'}, 'id': 'DEADBEEF'}

        document = json.dumps(obj, ensure_ascii=False)
        stream = io.StringIO(document)
        spec = [('body', dict), ('id', basestring)]
        filtered_object, = utils.filter_stream(stream, len(document), spec)

        self.assertEqual(filtered_object, obj)

        stream.seek(0)
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.filter_stream, stream, len(document), spec,
                          doctype=utils.JSONArray)

    def test_filter_stream_expect_array(self):
        array = [{u'body': {u'x': 1}}, {u'body': {u'x': 2}}]

        document = json.dumps(array, ensure_ascii=False)
        stream = io.StringIO(document)
        spec = [('body', dict)]
        filtered_objects = list(utils.filter_stream(
            stream, len(document), spec, doctype=utils.JSONArray))

        self.assertEqual(filtered_objects, array)

        stream.seek(0)
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.filter_stream, stream, len(document), spec,
                          doctype=utils.JSONObject)
