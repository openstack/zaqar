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

import io
import json

import falcon
import six
import testtools

from zaqar.transport.wsgi import utils


class TestUtils(testtools.TestCase):

    def test_get_checked_field_missing(self):
        doc = {}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack',
                          int, None)

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 42, int, None)

        doc = {'openstac': 10}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack',
                          int, None)

        value = utils.get_checked_field(doc, 'missing', int, 0)
        self.assertEqual(0, value)

        value = utils.get_checked_field(doc, 'missing', dict, {})
        self.assertEqual({}, value)

    def test_get_checked_field_bad_type(self):
        doc = {'openstack': '10'}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack',
                          int, None)

        doc = {'openstack': 10, 'openstack-mq': 'test'}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack',
                          str, None)

        doc = {'openstack': '[1, 2]'}

        self.assertRaises(falcon.HTTPBadRequest,
                          utils.get_checked_field, doc, 'openstack',
                          list, None)

    def test_get_checked_field(self):
        doc = {'hello': 'world', 'the answer': 42, 'question': []}

        value = utils.get_checked_field(doc, 'hello', str, None)
        self.assertEqual('world', value)

        value = utils.get_checked_field(doc, 'the answer', int, None)
        self.assertEqual(42, value)

        value = utils.get_checked_field(doc, 'question', list, None)
        self.assertEqual([], value)

    def test_filter_missing(self):
        doc = {'body': {'event': 'start_backup'}}
        spec = (('tag', dict, None),)
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.filter, doc, spec)

        spec = (('tag', str, 'db'),)
        filtered = utils.filter(doc, spec)
        self.assertEqual({'tag': 'db'}, filtered)

    def test_filter_bad_type(self):
        doc = {'ttl': '300', 'bogus': 'yogabbagabba'}
        spec = [('ttl', int, None)]
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.filter, doc, spec)

    def test_filter(self):
        doc = {'body': {'event': 'start_backup'}}

        def spec():
            yield ('body', dict, None)

        filtered = utils.filter(doc, spec())
        self.assertEqual(doc, filtered)

        doc = {'ttl': 300, 'bogus': 'yogabbagabba'}
        spec = [('ttl', int, None)]
        filtered = utils.filter(doc, spec)
        self.assertEqual({'ttl': 300}, filtered)

        doc = {'body': {'event': 'start_backup'}, 'ttl': 300}
        spec = (('body', dict, None), ('ttl', int, None))
        filtered = utils.filter(doc, spec)
        self.assertEqual(doc, filtered)

    def test_no_spec(self):
        obj = {u'body': {'event': 'start_backup'}, 'ttl': 300}
        document = six.text_type(json.dumps(obj, ensure_ascii=False))
        doc_stream = io.StringIO(document)

        deserialized = utils.deserialize(doc_stream, len(document))
        filtered = utils.sanitize(deserialized, spec=None)
        self.assertEqual(obj, filtered)

        # NOTE(kgriffs): Ensure default value for *spec* is None
        filtered2 = utils.sanitize(deserialized)
        self.assertEqual(filtered, filtered2)

    def test_no_spec_array(self):
        things = [{u'body': {'event': 'start_backup'}, 'ttl': 300}]
        document = six.text_type(json.dumps(things, ensure_ascii=False))
        doc_stream = io.StringIO(document)

        deserialized = utils.deserialize(doc_stream, len(document))
        filtered = utils.sanitize(deserialized, doctype=utils.JSONArray,
                                  spec=None)
        self.assertEqual(things, filtered)

    def test_filter_star(self):
        doc = {'ttl': 300, 'body': {'event': 'start_backup'}}

        spec = [('body', '*', None), ('ttl', '*', None)]
        filtered = utils.filter(doc, spec)

        self.assertEqual(doc, filtered)

    def test_deserialize_and_sanitize_json_obj(self):
        obj = {u'body': {'event': 'start_backup'}, 'id': 'DEADBEEF'}

        document = six.text_type(json.dumps(obj, ensure_ascii=False))
        stream = io.StringIO(document)
        spec = [('body', dict, None), ('id', six.string_types, None)]

        # Positive test
        deserialized_object = utils.deserialize(stream, len(document))
        filtered_object = utils.sanitize(deserialized_object, spec)
        self.assertEqual(obj, filtered_object)

        # Negative test
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.sanitize, deserialized_object, spec,
                          doctype=utils.JSONArray)

    def test_deserialize_and_sanitize_json_array(self):
        array = [{u'body': {u'x': 1}}, {u'body': {u'x': 2}}]

        document = six.text_type(json.dumps(array, ensure_ascii=False))
        stream = io.StringIO(document)
        spec = [('body', dict, None)]

        # Positive test
        deserialized_object = utils.deserialize(stream, len(document))
        filtered_object = utils.sanitize(deserialized_object, spec,
                                         doctype=utils.JSONArray)
        self.assertEqual(array, filtered_object)

        # Negative test
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.sanitize, deserialized_object, spec,
                          doctype=utils.JSONObject)

    def test_bad_doctype(self):
        self.assertRaises(TypeError,
                          utils.sanitize, {}, None, doctype=int)

    def test_deserialize_bad_stream(self):
        stream = None
        length = None
        self.assertRaises(falcon.HTTPBadRequest,
                          utils.deserialize, stream, length)
