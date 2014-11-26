"""
Tests for go_http.metrics.

"""

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


class TestMetricApiReader(TestCase):

    def setUp(self):
        self.session = TestSession()
        self.sender = MetricsApiClient(
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
                         "http://go.vumi.org/api/v1/go")

    def check_request(self, request, method, headers=None):
        self.assertEqual(request.method, method)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)

    def test_send_request(self):
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
            "metrics/?m=stores.store_name.metric_name.agg"
            "&interval=1d&from=-30d&nulls=omit", adapter)

        result = self.sender.get_metric(
            "stores.store_name.metric_name.agg", "-30d", "1d", "omit")
        self.assertEqual(result, response)
        self.check_request(
            adapter.request, 'GET',
            headers={"Authorization": u'Bearer auth-token'})
