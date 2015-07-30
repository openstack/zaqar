# Copyright (c) 2015 Red Hat, Inc.
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


class ExceptionBase(Exception):

    msg_format = ''

    def __init__(self, **kwargs):
        msg = self.msg_format.format(**kwargs)
        super(ExceptionBase, self).__init__(msg)


class BadRequest(ExceptionBase):
    """Raised when an invalid request is received."""

    msg_format = u'Bad request. {description}'

    def __init__(self, description):
        """Initializes the error with contextual information.

        :param description: Error description
        """

        super(BadRequest, self).__init__(description=description)


class DocumentTypeNotSupported(ExceptionBase):
    """Raised when the content of a request has an unsupported format."""
