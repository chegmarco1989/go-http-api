""" Tests for go_http.optouts.
"""

import json
from unittest import TestCase

from requests import HTTPError

from requests_testadapter import TestAdapter, TestSession

from go_http.optouts import OptOutsApiClient


class RecordingAdapter(TestAdapter):
    """ Record the request that was handled by the adapter.
    """
    request = None

    def send(self, request, *args, **kw):
        self.request = request
        return super(RecordingAdapter, self).send(request, *args, **kw)


class TestOptOutsApiClient(TestCase):

    def setUp(self):
        self.session = TestSession()
        self.client = OptOutsApiClient(
            auth_token="auth-token",
            api_url="http://example.com/api/v1/go",
            session=self.session)

    def response_ok(self, data):
        data.update({
            u'status': {
                u'reason': u'OK',
                u'code': 200,
            },
        })
        return data

    def test_default_session(self):
        import requests
        client = OptOutsApiClient(
            auth_token="auth-token")
        self.assertTrue(isinstance(client.session, requests.Session))

    def test_default_api_url(self):
        client = OptOutsApiClient(
            auth_token="auth-token")
        self.assertEqual(client.api_url,
                         "https://go.vumi.org/api/v1/go")

    def check_request(self, request, method, data=None, headers=None):
        self.assertEqual(request.method, method)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)
        if data is None:
            self.assertEqual(request.body, None)
        else:
            self.assertEqual(json.loads(request.body), data)

    def test_error_response(self):
        response = {
            u'status': {
                u'reason': u'Bad request',
                u'code': 400,
            },
        }
        adapter = RecordingAdapter(json.dumps(response), status=400)
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        self.assertRaises(
            HTTPError,
            self.client.get_optout, "msisdn", "+1234")
        self.check_request(
            adapter.request, 'GET',
            headers={"Authorization": u'Bearer auth-token'})

    def test_non_json_error_response(self):
        response = "Not JSON"
        adapter = RecordingAdapter(json.dumps(response), status=503)
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        self.assertRaises(
            HTTPError,
            self.client.get_optout, "msisdn", "+1234")

    def test_get_optout(self):
        opt_out = {
            u'created_at': u'2015-11-10 20:33:03.742409',
            u'message': None,
            u'user_account': u'fxxxeee',
        }
        response = self.response_ok({u'opt_out': opt_out})
        adapter = RecordingAdapter(json.dumps(response))
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        result = self.client.get_optout("msisdn", "+1234")
        self.assertEqual(result, opt_out)
        self.check_request(
            adapter.request, 'GET',
            headers={"Authorization": u'Bearer auth-token'})

    def test_get_optout_not_found(self):
        response = {
            u'status': {
                u'reason': u'Opt out not found',
                u'code': 404,
            },
        }
        adapter = RecordingAdapter(json.dumps(response), status=404)
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        result = self.client.get_optout("msisdn", "+1234")
        self.assertEqual(result, None)

    def test_set_optout(self):
        opt_out = {
            u'created_at': u'2015-11-10 20:33:03.742409',
            u'message': None,
            u'user_account': u'fxxxeee',
        }
        response = self.response_ok({u'opt_out': opt_out})
        adapter = RecordingAdapter(json.dumps(response))
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        result = self.client.set_optout("msisdn", "+1234")
        self.assertEqual(result, opt_out)
        self.check_request(
            adapter.request, 'PUT',
            headers={"Authorization": u'Bearer auth-token'})

    def test_delete_optout(self):
        opt_out = {
            u'created_at': u'2015-11-10 20:33:03.742409',
            u'message': None,
            u'user_account': u'fxxxeee',
        }
        response = self.response_ok({u'opt_out': opt_out})
        adapter = RecordingAdapter(json.dumps(response))
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        result = self.client.delete_optout("msisdn", "+1234")
        self.assertEqual(result, opt_out)
        self.check_request(
            adapter.request, 'DELETE',
            headers={"Authorization": u'Bearer auth-token'})

    def test_delete_optout_not_found(self):
        response = {
            u'status': {
                u'reason': u'Opt out not found',
                u'code': 404,
            },
        }
        adapter = RecordingAdapter(json.dumps(response), status=404)
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/msisdn/%2b1234", adapter)

        result = self.client.delete_optout("msisdn", "+1234")
        self.assertEqual(result, None)

    def test_count(self):
        response = self.response_ok({
            u'opt_out_count': 2,
        })
        adapter = RecordingAdapter(json.dumps(response))
        self.session.mount(
            "http://example.com/api/v1/go/"
            "optouts/count", adapter)

        result = self.client.count()
        self.assertEqual(result, 2)
        self.check_request(
            adapter.request, 'GET',
            headers={"Authorization": u'Bearer auth-token'})
