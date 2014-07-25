"""
Experimental client for Vumi Go's contacts API.

TODO:
 * Factor out common API-level code, such as auth.
 * Implement more of the API as the server side grows.
"""

import json

import requests


class ContactsApiClient(object):
    """
    Client for Vumi Go's contacts API.

    :param str auth_token:

        An OAuth 2 access token. NOTE: This will be replaced by a proper
        authentication system at some point.

    :param str api_url:
        The full URL of the HTTP API. Defaults to
        ``http://go.vumi.org/api/v1/go/contacts``.

    :type session:
        :class:`requests.Session`
    :param session:
        Requests session to use for HTTP requests. Defaults to a new session.
    """

    def __init__(self, auth_token, api_url=None, session=None):
        self.auth_token = auth_token
        if api_url is None:
            api_url = "http://go.vumi.org/api/v1/go/contacts"
        self.api_url = api_url.rstrip('/')
        if session is None:
            session = requests.Session()
        self.session = session

    def _api_request(self, method, api_path, data=None):
        url = "%s/%s" % (self.api_url, api_path)
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer %s" % (self.auth_token,),
        }
        if data is not None:
            data = json.dumps(data)
        r = self.session.request(method, url, data=data, headers=headers)
        r.raise_for_status()
        return r.json()

    def create_contact(self, contact_data):
        """
        Create a contact.

        :param dict contact_data:
            Data for new contact.
        """
        return self._api_request("POST", "", contact_data)

    def get_contact(self, contact_key):
        """
        Get a contact.

        :param str contact_key:
            Key for the contact to get.
        """
        return self._api_request("GET", contact_key)

    def delete_contact(self, contact_key):
        """
        Delete a contact.

        :param str contact_key:
            Key for the contact to delete.
        """
        return self._api_request("DELETE", contact_key)
