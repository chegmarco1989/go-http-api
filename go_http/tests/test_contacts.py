"""
Tests for go_http.contacts.
"""

import json
from unittest import TestCase

from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp, TestAdapter

from go_http.contacts import ContactsApiClient


class FakeContactsApi(object):
    """
    Fake implementation of the Vumi Go contacts API.
    """

    def __init__(self, auth_token, contacts_data):
        self.auth_token = auth_token
        self.contacts_data = contacts_data

    def handle_request(self, request):
        if not self.check_auth(request):
            return self.build_response("", 403)

        path = request.path_url.replace("/go/contacts/", "")
        # TODO: Improve this as our server implementation grows.
        if request.method == "GET":
            if "/" in path:
                return self.build_response("", 404)
            return self.get_contact(path, request)
        return self.build_response("", 405)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Resp(content, code, headers)

    def get_contact(self, path, request):
        contact = self.contacts_data.get(path)
        if contact is None:
            return self.build_response("Contact not found.", 404)
        return self.build_response(json.dumps(contact))


class FakeContactsApiAdapter(HTTPAdapter):
    """
    Adapter for FakeContactsApi.

    This inherits directly from HTTPAdapter instead of using TestAdapter
    because it overrides everything TestAdaptor does.
    """

    def __init__(self, contacts_api):
        self.contacts_api = contacts_api
        super(FakeContactsApiAdapter, self).__init__()

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        resp = self.contacts_api.handle_request(request)
        r = self.build_response(request, resp)
        if not stream:
            # force prefetching content unless streaming in use
            r.content
        return r


class TestContactsApiClient(TestCase):
    API_URL = "http://example.com/go/contacts"
    AUTH_TOKEN = "auth_token"

    def setUp(self):
        self.contacts_data = {}
        self.contacts_backend = FakeContactsApi(
            self.AUTH_TOKEN, self.contacts_data)
        self.session = TestSession()
        adapter = FakeContactsApiAdapter(self.contacts_backend)
        self.session.mount(self.API_URL, adapter)

    def make_client(self, auth_token=AUTH_TOKEN):
        return ContactsApiClient(
            auth_token, api_url=self.API_URL, session=self.session)

    def assert_http_error(self, expected_status, func, *args, **kw):
        try:
            func(*args, **kw)
        except HTTPError as err:
            self.assertEqual(err.response.status_code, expected_status)
        else:
            self.fail(
                "Expected HTTPError with status %s." % (expected_status,))

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
        import requests
        contacts = ContactsApiClient(self.AUTH_TOKEN)
        self.assertTrue(isinstance(contacts.session, requests.Session))

    def test_default_api_url(self):
        contacts = ContactsApiClient(self.AUTH_TOKEN)
        self.assertEqual(
            contacts.api_url, "http://go.vumi.org/api/v1/go/contacts")

    def test_auth_failure(self):
        contacts = self.make_client(auth_token="bogus_token")
        self.assert_http_error(403, contacts.get_contact, "foo")

    def test_get_missing_contact(self):
        contacts = self.make_client()
        self.assert_http_error(404, contacts.get_contact, "foo")

    def test_get_contact(self):
        # TODO: use a more realistic fake contact.
        contacts = self.make_client()
        self.contacts_data[u"contact-1"] = {u"foo": u"bar"}
        contact = contacts.get_contact("contact-1")
        self.assertEqual(contact, {u"foo": u"bar"})
