# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common utility classes and functions for testing."""
import io

import firebase_admin
from google.auth import credentials, transport
from requests import adapters, models


class MockResponse(transport.Response):
    def __init__(self, status, response):
        self._status = status
        self._response = response

    @property
    def status(self):
        return self._status

    @property
    def headers(self):
        return {}

    @property
    def data(self):
        return self._response.encode()


class MockRequest(transport.Request):
    """A mock HTTP requests implementation.

    This can be used whenever an HTTP interaction needs to be mocked
    for testing purposes. For example HTTP calls to fetch public key
    certificates, and HTTP calls to retrieve access tokens can be
    mocked using this class.
    """

    def __init__(self, status, response):
        self.response = MockResponse(status, response)
        self.log = []

    def __call__(self, *args, **kwargs):  # pylint: disable=arguments-differ
        self.log.append((args, kwargs))
        return self.response


class MockFailedRequest(transport.Request):
    """A mock HTTP request that fails by raising an exception."""

    def __init__(self, error):
        self.error = error
        self.log = []

    def __call__(self, *args, **kwargs):  # pylint: disable=arguments-differ
        self.log.append((args, kwargs))
        raise self.error


class MockGoogleCredential(credentials.Credentials):
    """A mock Google authentication credential."""

    def refresh(self, request):
        self.token = "mock-token"


class MockCredential(firebase_admin.credentials.Base):
    """A mock Firebase credential implementation."""

    def __init__(self):
        self._g_credential = MockGoogleCredential()

    def get_credential(self):
        return self._g_credential


class MockMultiRequestAdapter(adapters.HTTPAdapter):
    """A mock HTTP adapter that supports multiple responses for the Python requests module."""

    def __init__(self, responses, statuses, recorder):
        """Constructs a MockMultiRequestAdapter.

        The lengths of the responses and statuses parameters must match.

        Each incoming request consumes a response and a status, in order. If all responses and
        statuses are exhausted, further requests will reuse the last response and status.
        """
        adapters.HTTPAdapter.__init__(self)
        if len(responses) != len(statuses):
            raise ValueError("The lengths of responses and statuses do not match.")
        self._current_response = 0
        self._responses = list(responses)  # Make a copy.
        self._statuses = list(statuses)
        self._recorder = recorder

    def send(self, request, **kwargs):  # pylint: disable=arguments-differ
        request._extra_kwargs = kwargs
        self._recorder.append(request)
        resp = models.Response()
        resp.url = request.url
        resp.status_code = self._statuses[self._current_response]
        resp.raw = io.BytesIO(self._responses[self._current_response].encode())
        self._current_response = min(
            self._current_response + 1, len(self._responses) - 1
        )
        return resp


class MockAdapter(MockMultiRequestAdapter):
    """A mock HTTP adapter for the Python requests module."""

    def __init__(self, data, status, recorder):
        super(MockAdapter, self).__init__([data], [status], recorder)

    @property
    def status(self):
        return self._statuses[0]

    @property
    def data(self):
        return self._responses[0]
