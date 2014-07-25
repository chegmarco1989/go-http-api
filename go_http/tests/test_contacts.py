"""
Tests for go_http.contacts.
"""

import json
from uuid import uuid4
from unittest import TestCase

from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp, TestAdapter

from go_http.contacts import ContactsApiClient


def make_contact_dict(fields):
    contact = {
        # Always generate a key. It can be overridden by `fields`.
        u'key': uuid4().hex,

        # Some constant-for-our-purposes fields.
        u'$VERSION': 2,
        u'user_account': u'owner-1',
        u'created_at': u'2014-07-25 12:44:11.159151',

        # Everything else.
        u'name': None,
        u'surname': None,
        u'groups': [],
        u'msisdn': None,
        u'twitter_handle': None,
        u'bbm_pin': None,
        u'mxit_id': None,
        u'dob': None,
        u'facebook_id': None,
        u'wechat_id': None,
        u'email_address': None,
        u'gtalk_id': None,
    }
    contact.update(fields)
    return contact


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

        # TODO: Improve this as our server implementation grows.

        contact_key = request.path_url.replace("/go/contacts", "").lstrip("/")
        if not contact_key:
            if request.method == "POST":
                return self.create_contact(request)
            else:
                return self.build_response("", 405)

        if request.method == "GET":
            return self.get_contact(contact_key, request)
        elif request.method == "DELETE":
            return self.delete_contact(contact_key, request)
        else:
            return self.build_response("", 405)

    def check_auth(self, request):
        auth_header = request.headers.get("Authorization")
        return auth_header == "Bearer %s" % (self.auth_token,)

    def build_response(self, content, code=200, headers=None):
        return Resp(content, code, headers)

    def create_contact(self, request):
        # TODO: Confirm this behaviour against the real API.
        contact_data = json.loads(request.body)
        if u"key" in contact_data:
            return self.build_response("", 400)
        contact = make_contact_dict(contact_data)
        self.contacts_data[contact[u"key"]] = contact
        return self.build_response(json.dumps(contact))

    def get_contact(self, contact_key, request):
        # TODO: Confirm this behaviour against the real API.
        contact = self.contacts_data.get(contact_key)
        if contact is None:
            return self.build_response("Contact not found.", 404)
        return self.build_response(json.dumps(contact))

    def delete_contact(self, contact_key, request):
        # TODO: Confirm this behaviour against the real API.
        contact = self.contacts_data.pop(contact_key, None)
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

    def make_existing_contact(self, contact_data):
        existing_contact = make_contact_dict(contact_data)
        self.contacts_data[existing_contact[u"key"]] = existing_contact
        return existing_contact

    def assert_contact_status(self, contact_key, exists=True):
        exists_status = (contact_key in self.contacts_data)
        self.assertEqual(exists_status, exists)

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

    def test_create_contact(self):
        contacts = self.make_client()
        contact_data = {
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        }
        contact = contacts.create_contact(contact_data)

        expected_contact = make_contact_dict(contact_data)
        # The key is generated for us.
        expected_contact[u"key"] = contact[u"key"]
        self.assertEqual(contact, expected_contact)
        self.assert_contact_status(contact[u"key"], exists=True)

    def test_create_contact_with_key(self):
        contacts = self.make_client()
        contact_data = {
            u"key": u"foo",
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        }
        self.assert_http_error(400, contacts.create_contact, contact_data)
        self.assert_contact_status(u"foo", exists=False)

    def test_get_contact(self):
        contacts = self.make_client()
        existing_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })

        contact = contacts.get_contact(existing_contact[u"key"])
        self.assertEqual(contact, existing_contact)

    def test_get_missing_contact(self):
        contacts = self.make_client()
        self.assert_http_error(404, contacts.get_contact, "foo")

    def test_delete_contact(self):
        contacts = self.make_client()
        existing_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })

        self.assert_contact_status(existing_contact[u"key"], exists=True)
        contact = contacts.delete_contact(existing_contact[u"key"])
        self.assertEqual(contact, existing_contact)
        self.assert_contact_status(existing_contact[u"key"], exists=False)

    def test_delete_missing_contact(self):
        contacts = self.make_client()
        self.assert_http_error(404, contacts.delete_contact, "foo")
