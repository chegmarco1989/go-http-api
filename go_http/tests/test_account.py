"""
Tests for go_http.account
"""

import collections
import copy
import json
from unittest import TestCase

from requests import HTTPError, Session
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp, TestAdapter

from go_http.account import AccountApiClient
from go_http.exceptions import JsonRpcException
from go_http.tests.fixtures import account as fixtures


class FakeAccountApiAdapter(HTTPAdapter):
    """
    Adapter providing a fake account API.

    This inherits directly from HTTPAdapter instead of using TestAdapter
    because it overrides everything TestAdaptor does.
    """

    def __init__(self, account_api):
        self.account_api = account_api
        super(FakeAccountApiAdapter, self).__init__()

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        response = self.account_api.handle_request(request)
        r = self.build_response(request, response)
        if not stream:
            # force prefetching content unless streaming in use
            r.content
        return r


class FakeAccountApi(object):
    def __init__(self, api_path, auth_token):
        self.api_path = api_path
        self.auth_token = auth_token
        self.responses = collections.defaultdict(list)

    def http_error_response(self, http_code, error):
        return Resp("403 Forbidden", 403, headers={})

    def jsonrpc_error_response(self, fault, fault_code, fault_string):
        return Resp(json.dumps({
            "error": {
                "fault": fault, "faultCode": fault_code,
                "faultString": fault_string,
            },
        }), 200, headers={})

    def jsonrpc_success_response(self, result):
        return Resp(json.dumps({
            "error": None,
            "result": result,
        }), 200, headers={})

    def add_success_response(self, method, params, result):
        self.responses[method].append((params, copy.deepcopy(result), None))

    def add_error_response(self, method, params, **error):
        self.responses[method].append((params, None, error))

    def handle_request(self, request):
        if request.headers['Authorization'] != 'Bearer %s' % (
                self.auth_token):
            return self.http_error_response(403, "403 Forbidden")
        if request.headers['Content-Type'] != (
                'application/json; charset=utf-8'):
            return self.http_error_response(400, "Invalid Content-Type.")
        if request.method != "POST":
            return self.jsonrpc_error_response(
                "Fault", 8000, "Only POST method supported")
        data = json.loads(request.body)
        params, result, error = self.responses[data['method']].pop()
        assert params == data['params']
        if error is not None:
            return self.jsonrpc_error_response(**error)
        return self.jsonrpc_success_response(result)


class TestAccountApiClient(TestCase):
    API_URL = "http://example.com/go"
    AUTH_TOKEN = "auth_token"

    def setUp(self):
        self.account_backend = FakeAccountApi("go/", self.AUTH_TOKEN)
        self.session = TestSession()
        self.adapter = FakeAccountApiAdapter(self.account_backend)
        self.simulate_api_up()

    def simulate_api_down(self):
        self.session.mount(self.API_URL, TestAdapter("API is down", 500))

    def simulate_api_up(self):
        self.session.mount(self.API_URL, self.adapter)

    def make_client(self, auth_token=AUTH_TOKEN):
        return AccountApiClient(
            auth_token, api_url=self.API_URL, session=self.session)

    def assert_http_error(self, expected_status, func, *args, **kw):
        try:
            func(*args, **kw)
        except HTTPError as err:
            self.assertEqual(err.response.status_code, expected_status)
        else:
            self.fail(
                "Expected HTTPError with status %s." % (expected_status,))

    def assert_jsonrpc_exception(self, f, *args, **kw):
        try:
            f(*args, **kw)
        except Exception as err:
            self.assertTrue(isinstance(err, JsonRpcException))
            self.assertTrue(isinstance(err.fault, unicode))
            self.assertTrue(isinstance(err.fault_code, int))
            self.assertTrue(isinstance(err.fault_string, unicode))
        return err

    def test_assert_http_error(self):
        self.session.mount("http://bad.example.com/", TestAdapter("", 500))

        def bad_req():
            r = self.session.get("http://bad.example.com/")
            r.raise_for_status()

        # Fails when no exception is raised.
        self.assertRaises(
            self.failureException, self.assert_http_error, 404, lambda: None)

        # Fails when an HTTPError with the wrong status code is raised.
        self.assertRaises(
            self.failureException, self.assert_http_error, 404, bad_req)

        # Passes when an HTTPError with the expected status code is raised.
        self.assert_http_error(500, bad_req)

        # Non-HTTPError exceptions aren't caught.
        def raise_error():
            raise ValueError()

        self.assertRaises(ValueError, self.assert_http_error, 404, raise_error)

    def test_default_session(self):
        client = AccountApiClient(self.AUTH_TOKEN)
        self.assertTrue(isinstance(client.session, Session))

    def test_default_api_url(self):
        client = AccountApiClient(self.AUTH_TOKEN)
        self.assertEqual(
            client.api_url, "https://go.vumi.org/api/v1/go")

    def test_auth_failure(self):
        client = self.make_client(auth_token="bogus_token")
        self.assert_http_error(403, client.campaigns)

    def test_jsonrpc_error_handling(self):
        client = self.make_client()
        self.account_backend.add_error_response(
            "campaigns", [],
            fault="Fault", fault_code=8002, fault_string="Meep")
        err = self.assert_jsonrpc_exception(client.campaigns)
        self.assertEqual(err.fault, "Fault")
        self.assertEqual(err.fault_code, 8002)
        self.assertEqual(err.fault_string, "Meep")

    def test_campaigns(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "campaigns", [], fixtures.campaigns)
        self.assertEqual(client.campaigns(), fixtures.campaigns)

    def test_conversations(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "conversations", ["campaign-1"], fixtures.conversations)
        self.assertEqual(
            client.conversations("campaign-1"),
            fixtures.conversations)

    def test_channels(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "channels", ["campaign-1"], fixtures.channels)
        self.assertEqual(
            client.channels("campaign-1"),
            fixtures.channels)

    def test_routers(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "routers", ["campaign-1"], fixtures.routers)
        self.assertEqual(
            client.routers("campaign-1"),
            fixtures.routers)

    def test_routing_entries(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "routing_entries", ["campaign-1"], fixtures.routing_entries)
        self.assertEqual(
            client.routing_entries("campaign-1"),
            fixtures.routing_entries)

    def test_routing_table(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "routing_table", ["campaign-1"], fixtures.routing_table)
        self.assertEqual(
            client.routing_table("campaign-1"),
            fixtures.routing_table)

    def test_update_routing_tabel(self):
        client = self.make_client()
        self.account_backend.add_success_response(
            "update_routing_table", ["campaign-1", fixtures.routing_table],
            None)
        self.assertEqual(
            client.update_routing_table("campaign-1", fixtures.routing_table),
            None)
