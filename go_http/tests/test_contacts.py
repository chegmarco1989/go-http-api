"""
Tests for go_http.contacts.
"""

from unittest import TestCase

from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp, TestAdapter

from fake_go_contacts import Request, FakeContactsApi

from go_http.contacts import ContactsApiClient


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
        req = Request(
            request.method, request.path_url, request.body, request.headers)
        resp = self.contacts_api.handle_request(req)
        response = Resp(resp.body, resp.code, resp.headers)
        r = self.build_response(request, response)
        if not stream:
            # force prefetching content unless streaming in use
            r.content
        return r


make_contact_dict = FakeContactsApi.make_contact_dict
make_group_dict = FakeContactsApi.make_group_dict


class TestContactsApiClient(TestCase):
    API_URL = "http://example.com/go"
    AUTH_TOKEN = "auth_token"

    MAX_CONTACTS_PER_PAGE = 10

    def setUp(self):
        self.contacts_data = {}
        self.groups_data = {}
        self.contacts_backend = FakeContactsApi(
            "go/", self.AUTH_TOKEN, self.contacts_data, self.groups_data,
            contacts_limit=self.MAX_CONTACTS_PER_PAGE)
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

    def make_existing_group(self, group_data):
        existing_group = make_group_dict(group_data)
        self.groups_data[existing_group[u'key']] = existing_group
        return existing_group

    def assert_contact_status(self, contact_key, exists=True):
        exists_status = (contact_key in self.contacts_data)
        self.assertEqual(exists_status, exists)

    def assert_group_status(self, group_key, exists=True):
        exists_status = (group_key in self.groups_data)
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
            contacts.api_url, "http://go.vumi.org/api/v1/go")

    def test_auth_failure(self):
        contacts = self.make_client(auth_token="bogus_token")
        self.assert_http_error(403, contacts.get_contact, "foo")

    def test_contacts_single_page(self):
        expected_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })
        contacts_api = self.make_client()
        [contact] = list(contacts_api.contacts())
        self.assertEqual(contact, expected_contact)

    def test_contacts_no_results(self):
        contacts_api = self.make_client()
        contacts = list(contacts_api.contacts())
        self.assertEqual(contacts, [])

    def test_contacts_multiple_pages(self):
        expected_contacts = []
        for i in range(self.MAX_CONTACTS_PER_PAGE + 1):
            expected_contacts.append(self.make_existing_contact({
                u"msisdn": u"+155564%d" % (i,),
                u"name": u"Arthur",
                u"surname": u"of Camelot",
            }))
        contacts_api = self.make_client()
        contacts = list(contacts_api.contacts())

        contacts.sort(key=lambda d: d['msisdn'])
        expected_contacts.sort(key=lambda d: d['msisdn'])

        self.assertEqual(contacts, expected_contacts)

    def test_contacts_multiple_pages_with_cursor(self):
        expected_contacts = []
        for i in range(self.MAX_CONTACTS_PER_PAGE):
            expected_contacts.append(self.make_existing_contact({
                u"msisdn": u"+155564%d" % (i,),
                u"name": u"Arthur",
                u"surname": u"of Camelot",
            }))
        expected_contacts.append(self.make_existing_contact({
            u"msisdn": u"+15556",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        }))
        contacts_api = self.make_client()
        first_page = contacts_api._api_request("GET", "contacts", "")
        cursor = first_page['cursor']
        contacts = list(contacts_api.contacts(start_cursor=cursor))
        contacts.extend(first_page['data'])
        contacts.sort(key=lambda d: d['msisdn'])
        expected_contacts.sort(key=lambda d: d['msisdn'])
        self.assertEqual(contacts, expected_contacts)

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

    def test_create_contact_with_extras(self):
        contacts = self.make_client()
        contact_data = {
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
            u"extra": {
                u"quest": u"Grail",
                u"sidekick": u"Percy",
            },
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

    def test_get_contact_with_extras(self):
        contacts = self.make_client()
        existing_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
            u"extra": {
                u"quest": u"Grail",
                u"sidekick": u"Percy",
            },
        })

        contact = contacts.get_contact(existing_contact[u"key"])
        self.assertEqual(contact, existing_contact)

    def test_get_missing_contact(self):
        contacts = self.make_client()
        self.assert_http_error(404, contacts.get_contact, "foo")

    def test_get_contact_from_field(self):
        contacts = self.make_client()
        existing_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })

        contact = contacts.get_contact(msisdn='+15556483')
        self.assertEqual(contact, existing_contact)

    def test_get_contact_from_field_missing(self):
        contacts = self.make_client()
        self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })

        self.assert_http_error(
            400, contacts.get_contact, msisdn='+12345')

    def test_update_contact(self):
        contacts = self.make_client()
        existing_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
        })

        new_contact = existing_contact.copy()
        new_contact[u"surname"] = u"Pendragon"

        contact = contacts.update_contact(
            existing_contact[u"key"], {u"surname": u"Pendragon"})
        self.assertEqual(contact, new_contact)

    def test_update_contact_with_extras(self):
        contacts = self.make_client()
        existing_contact = self.make_existing_contact({
            u"msisdn": u"+15556483",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
            u"extra": {
                u"quest": u"Grail",
                u"sidekick": u"Percy",
            },
        })

        new_contact = existing_contact.copy()
        new_contact[u"surname"] = u"Pendragon"
        new_contact[u"extra"] = {
            u"quest": u"lunch",
            u"knight": u"Lancelot",
        }

        contact = contacts.update_contact(existing_contact[u"key"], {
            u"surname": u"Pendragon",
            u"extra": {
                u"quest": u"lunch",
                u"knight": u"Lancelot",
            },
        })
        self.assertEqual(contact, new_contact)

    def test_update_missing_contact(self):
        contacts = self.make_client()
        self.assert_http_error(404, contacts.update_contact, "foo", {})

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

    def test_create_group(self):
        client = self.make_client()
        group_data = {
            u'name': u'Bob',
        }
        group = client.create_group(group_data)

        expected_group = make_group_dict(group_data)
        # The key is generated for us.
        expected_group[u'key'] = group[u'key']
        self.assertEqual(group, expected_group)
        self.assert_group_status(group[u'key'], exists=True)

    def test_create_smart_group(self):
        client = self.make_client()
        group_data = {
            u'name': u'Bob',
            u'query': u'test-query',
        }
        group = client.create_group(group_data)

        expected_group = make_group_dict(group_data)
        # The key is generated for us
        expected_group[u'key'] = group[u'key']
        self.assertEqual(group, expected_group)
        self.assert_group_status(group[u'key'], exists=True)

    def test_create_group_with_key(self):
        client = self.make_client()
        group_data = {
            u'key': u'foo',
            u'name': u'Bob',
            u'query': u'test-query',
        }
        self.assert_http_error(400, client.create_group, group_data)

    def test_get_group(self):
        client = self.make_client()
        existing_group = self.make_existing_group({
            u'name': 'Bob',
        })
        group = client.get_group(existing_group[u'key'])
        self.assertEqual(group, existing_group)

    def test_get_smart_group(self):
        client = self.make_client()
        existing_group = self.make_existing_group({
            u'name': 'Bob',
            u'query': 'test-query',
        })
        group = client.get_group(existing_group[u'key'])
        self.assertEqual(group, existing_group)

    def test_get_missing_group(self):
        client = self.make_client()
        self.assert_http_error(404, client.get_group, 'foo')

    def test_update_group(self):
        client = self.make_client()
        existing_group = self.make_existing_group({
            u'name': u'Bob',
        })

        new_group = existing_group.copy()
        new_group[u'name'] = u'Susan'

        group = client.update_group(existing_group[u'key'],
                                    {'name': 'Susan'})
        self.assertEqual(existing_group, group)
        self.assertEqual(group, new_group)

    def test_update_smart_group(self):
        client = self.make_client()
        existing_group = self.make_existing_group({
            u'name': u'Bob',
            u'query': u'test-query',
        })

        new_group = existing_group.copy()
        new_group[u'query'] = u'another-query'

        group = client.update_group(existing_group[u'key'],
                                    {'query': 'another-query'})
        self.assertEqual(existing_group, group)
        self.assertEqual(group, new_group)

    def test_update_missing_group(self):
        client = self.make_client()
        self.assert_http_error(404, client.update_group, 'foo', {})

    def test_delete_group(self):
        client = self.make_client()
        existing_group = self.make_existing_group({
            u'name': u'Bob'
        })

        self.assert_group_status(existing_group[u'key'], exists=True)
        group = client.delete_group(existing_group[u'key'])
        self.assertEqual(existing_group, group)
        self.assert_group_status(group[u'key'], exists=False)

    def test_delete_missing_group(self):
        client = self.make_client()
        self.assert_http_error(404, client.delete_group, 'foo')
