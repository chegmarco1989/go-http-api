""" Client for Vumi Go's opt out API.
"""

import json
import urllib

import requests


class OptOutsApiClient(object):
    """
    Client for Vumi Go's opt out API.

    :param str auth_token:
        An OAuth 2 access token.

    :param str api_url:
        The full URL of the HTTP API. Defaults to
        ``https://go.vumi.org/api/v1/go``.

    :type session:
        :class:`requests.Session`
    :param session:
        Requests session to use for HTTP requests. Defaults to a new session.
    """

    def __init__(self, auth_token, api_url=None, session=None):
        self.auth_token = auth_token
        if api_url is None:
            api_url = "https://go.vumi.org/api/v1/go"
        self.api_url = api_url.rstrip('/')
        if session is None:
            session = requests.Session()
        self.session = session

    def _api_request(self, method, path, data=None, none_for_statuses=()):
        url = "%s/%s" % (self.api_url, urllib.quote(path))
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer %s" % (self.auth_token,),
        }
        if method is "GET" and data is not None:
            r = self.session.request(method, url, params=data, headers=headers)
        else:
            if data is not None:
                data = json.dumps(data)
            r = self.session.request(method, url, data=data, headers=headers)
        if r.status_code in none_for_statuses:
            return None
        r.raise_for_status()
        return r.json()

    def get_optout(self, address_type, address):
        """
        Retrieve an opt out record.

        :param str address_type:
            Type of address, e.g. `msisdn`.
        :param str address:
            The address to retrieve an opt out for, e.g. `+271235678`.

        :return:
            The opt out record (a dict) or `None` if the API returned a 404
            HTTP response.

        Example::

            >>> client.get_optout('msisdn', '+12345')
            {
                u'created_at': u'2015-11-10 20:33:03.742409',
                u'message': None,
                u'user_account': u'fxxxeee',
            }
        """
        uri = "optouts/%s/%s" % (address_type, address)
        result = self._api_request("GET", uri, none_for_statuses=(404,))
        if result is None:
            return None
        return result["opt_out"]

    def set_optout(self, address_type, address):
        """
        Register an address as having opted out.

        :param str address_type:
            Type of address, e.g. `msisdn`.
        :param str address:
            The address to store an opt out for, e.g. `+271235678`.

        :return:
            The created opt out record (a dict).

        Example::

            >>> client.set_optout('msisdn', '+12345')
            {
                u'created_at': u'2015-11-10 20:33:03.742409',
                u'message': None,
                u'user_account': u'fxxxeee',
            }
        """
        uri = "optouts/%s/%s" % (address_type, address)
        result = self._api_request("PUT", uri)
        return result["opt_out"]

    def delete_optout(self, address_type, address):
        """
        Remove an out opt record.

        :param str address_type:
            Type of address, e.g. `msisdn`.
        :param str address:
            The address to remove the opt out record for, e.g. `+271235678`.

        :return:
            The deleted opt out record (a dict) or None if the API returned
            an HTTP 404 reponse.

        Example::

            >>> client.delete_optout('msisdn', '+12345')
            {
                u'created_at': u'2015-11-10 20:33:03.742409',
                u'message': None,
                u'user_account': u'fxxxeee',
            }
        """
        uri = "optouts/%s/%s" % (address_type, address)
        result = self._api_request("DELETE", uri, none_for_statuses=(404,))
        if result is None:
            return None
        return result["opt_out"]

    def count(self):
        """
        Return a count of the total number of opt out records.

        :return:
            The total number of opt outs (an integer).

        Example::

            >>> client.count()
            215
        """
        uri = "optouts/count"
        result = self._api_request("GET", uri)
        return result["opt_out_count"]
