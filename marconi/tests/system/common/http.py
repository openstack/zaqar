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

import json
import requests


def get(url, header=''):
    """Does  http GET."""
    if header:
        header = json.loads(header)
    try:
        response = requests.get(url, headers=header)
    except requests.ConnectionError as detail:
        print('ConnectionError: Exception in http.get {}'.format(detail))
    except requests.HTTPError as detail:
        print('HTTPError: Exception in http.get {}'.format(detail))
    except requests.Timeout as detail:
        print('Timeout: Exception in http.get {}'.format(detail))
    except requests.TooManyRedirects as detail:
        print('TooManyRedirects: Exception in http.get {}'.format(detail))
    return response


def post(url, header='', body=''):
    """Does  http POST."""
    if header:
        header = json.loads(header)
    body = str(body)
    body = body.replace("'", '"')
    try:
        response = requests.post(url, headers=header, data=body)
    except requests.ConnectionError as detail:
        print('ConnectionError: Exception in http.post {}'.format(detail))
    except requests.HTTPError as detail:
        print('HTTPError: Exception in http.post {}'.format(detail))
    except requests.Timeout as detail:
        print('Timeout: Exception in http.post {}'.format(detail))
    except requests.TooManyRedirects as detail:
        print('TooManyRedirects: Exception in http.post {}'.format(detail))
    return response


def put(url, header='', body=''):
    """Does  http PUT."""
    response = None
    if header:
        header = json.loads(header)

    try:
        response = requests.put(url, headers=header, data=body)
    except requests.ConnectionError as detail:
        print('ConnectionError: Exception in http.put {}'.format(detail))
    except requests.HTTPError as detail:
        print('HTTPError: Exception in http.put {}'.format(detail))
    except requests.Timeout as detail:
        print('Timeout: Exception in http.put {}'.format(detail))
    except requests.TooManyRedirects as detail:
        print('TooManyRedirects: Exception in http.put {}'.format(detail))
    return response


def delete(url, header=''):
    """Does  http DELETE."""
    response = None
    if header:
        header = json.loads(header)

    try:
        response = requests.delete(url, headers=header)
    except requests.ConnectionError as detail:
        print('ConnectionError: Exception in http.delete {}'.format(detail))
    except requests.HTTPError as detail:
        print('HTTPError: Exception in http.delete {}'.format(detail))
    except requests.Timeout as detail:
        print('Timeout: Exception in http.delete {}'.format(detail))
    except requests.TooManyRedirects as detail:
        print('TooManyRedirects: Exception in http.delete {}'.format(detail))
    return response


def patch(url, header='', body=''):
    """Does  http PATCH."""
    response = None
    if header:
        header = json.loads(header)

    try:
        response = requests.patch(url, headers=header, data=body)
    except requests.ConnectionError as detail:
        print('ConnectionError: Exception in http.patch {}'.format(detail))
    except requests.HTTPError as detail:
        print('HTTPError: Exception in http.patch {}'.format(detail))
    except requests.Timeout as detail:
        print('Timeout: Exception in http.patch {}'.format(detail))
    except requests.TooManyRedirects as detail:
        print('TooManyRedirects: Exception in http.patch {}'.format(detail))
    return response
