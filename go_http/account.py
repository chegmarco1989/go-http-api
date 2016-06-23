"""
Client for Vumi Go's JSON-RPC based account, conversations, channel and
routing API.
"""

import json

import requests

from go_http.exceptions import JsonRpcException


class AccountApiClient(object):
    """
    Client for Vumi Go's JSON-RPC based account, conversations, channel and
    routing API.

    :param str auth_token:
        An OAuth 2 access token. NOTE: This will be replaced by a proper
        authentication system at some point.

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

    def _api_request(self, method, params):
        url = "%s/api/" % (self.api_url,)
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer %s" % (self.auth_token,),
        }
        data = {
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
            "id": 0,
        }
        r = self.session.post(url, data=json.dumps(data), headers=headers)
        r.raise_for_status()
        rpc_response = r.json()
        rpc_error = rpc_response['error']
        if rpc_error is not None:
            raise JsonRpcException(
                fault=rpc_error['fault'], fault_code=rpc_error['faultCode'],
                fault_string=rpc_error['faultString'])
        return rpc_response['result']

    def campaigns(self):
        """
        Return a list of campaigns accessible by the account.

        Note: The server-side implementation of this API method is a stub. It
        always returns a single campaign whose name is 'Your Campaign' and
        whose key is the account key.
        """
        return self._api_request("campaigns", [])

    def conversations(self, campaign_id):
        """
        Return a list of conversations for the campaign.

        :param str campaign_id:
            The campaign or account id.
        """
        return self._api_request("conversations", [campaign_id])

    def channels(self, campaign_id):
        """
        Return a list of channels for the campaign.

        :param str campaign_id:
            The campaign or account id.
        """
        return self._api_request("channels", [campaign_id])

    def routers(self, campaign_id):
        """
        Return a list of routers for the campaign.

        :param str campaign_id:
            The campaign or account id.
        """
        return self._api_request("routers", [campaign_id])

    def routing_entries(self, campaign_id):
        """
        Return a list of routing entries for the campaign.

        :param str campaign_id:
            The campaign or account id.
        """
        return self._api_request("routing_entries", [campaign_id])

    def routing_table(self, campaign_id):
        """
        Return the complete routing table for the campaign.

        :param str campaign_id:
            The campaign or account id.
        """
        return self._api_request("routing_table", [campaign_id])

    def update_routing_table(self, campaign_id, routing_table):
        """
        Update the routing table for the campaign.

        :param str campaign_id:
            The campaign or account id.
        :param dict routing_table:
            The complete new routing table.
        """
        return self._api_request(
            "update_routing_table", [campaign_id, routing_table])
