"""
Tests for go_http.metrics.
"""

import urlparse
import json
from unittest import TestCase

from requests_testadapter import TestAdapter, TestSession

from go_http.metrics import MetricsApiClient


class RecordingAdapter(TestAdapter):

    """ Record the request that was handled by the adapter.
    """
    request = None

    def send(self, request, *args, **kw):
        self.request = request
        return super(RecordingAdapter, self).send(request, *args, **kw)


class TestMetricApiClient(TestCase):

    def setUp(self):
        self.session = TestSession()
        self.client = MetricsApiClient(
            auth_token="auth-token",
            api_url="http://example.com/api/v1/go",
            session=self.session)

    def test_default_session(self):
        import requests
        client = MetricsApiClient(
            auth_token="auth-token")
        self.assertTrue(isinstance(client.session, requests.Session))

    def test_default_api_url(self):
        client = MetricsApiClient(
            auth_token="auth-token")
        self.assertEqual(client.api_url,
                         "https://go.vumi.org/api/v1/go")

    def check_request(
            self, request, method, params=None, data=None, headers=None):
        self.assertEqual(request.method, method)
        if params is not None:
            url = urlparse.urlparse(request.url)
            qs = urlparse.parse_qsl(url.query)
            self.assertEqual(dict(qs), params)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)
        if data is None:
            self.assertEqual(request.body, None)
        else:
            self.assertEqual(json.loads(request.body), data)

    def test_get_metric(self):
        response = {u'stores.store_name.metric_name.agg':
                    [{u'x': 1413936000000,
                        u'y': 88916.0},
                     {u'x': 1414022400000,
                        u'y': 91339.0},
                     {u'x': 1414108800000,
                        u'y': 92490.0},
                     {u'x': 1414195200000,
                        u'y': 92655.0},
                     {u'x': 1414281600000,
                        u'y': 92786.0}]}
        adapter = RecordingAdapter(json.dumps(response))
        self.session.mount(
            "http://example.com/api/v1/go/"
            "metrics/", adapter)

        result = self.client.get_metric(
            "stores.store_name.metric_name.agg", "-30d", "1d", "omit")
        self.assertEqual(result, response)
        self.check_request(
            adapter.request, 'GET',
            params={
                "m": "stores.store_name.metric_name.agg",
                "interval": "1d",
                "from": "-30d", "nulls": "omit"},
            headers={"Authorization": u'Bearer auth-token'})

    def test_fire(self):
        response = [{
            'name': 'foo.last',
            'value': 3.1415,
            'aggregator': 'last',
        }]
        adapter = RecordingAdapter(json.dumps(response))
        self.session.mount(
            "http://example.com/api/v1/go/"
            "metrics/", adapter)

        result = self.client.fire({
            "foo.last": 3.1415,
        })
        self.assertEqual(result, response)
        self.check_request(
            adapter.request, 'POST',
            data={"foo.last": 3.1415},
            headers={"Authorization": u'Bearer auth-token'})
