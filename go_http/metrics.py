"""
Experimental client for Vumi Go's metrics API.

TODO:
 * Factor out common API-level code, such as auth.
 * Implement more of the API as the server side grows.
"""

import json

import requests


class MetricsApiClient(object):
    """
    Client for Vumi Go's metrics API.

    :param str auth_token:

        An OAuth 2 access token. NOTE: This will be replaced by a proper
        authentication system at some point.

    :param str api_url:
        The full URL of the HTTP API. Defaults to
        ``http://go.vumi.org/api/v1/go``.

    :type session:
        :class:`requests.Session`
    :param session:
        Requests session to use for HTTP requests. Defaults to a new session.
    """

    def __init__(self, auth_token, api_url=None, session=None):
        self.auth_token = auth_token
        if api_url is None:
            api_url = "http://go.vumi.org/api/v1/go"
        self.api_url = api_url.rstrip('/')
        if session is None:
            session = requests.Session()
        self.session = session

    def _api_request(self, method, api_collection, data=None):
        url = "%s/%s" % (self.api_url, api_collection)
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
        r.raise_for_status()
        return r.json()

    def get_metric(self, metric, start, interval, nulls):
        """
        Get a metric.

        :param str metric:
            Metric name.
        :param str start:
            How far back to get metrics from (e.g. `-30d`).
        :param str interval:
            Bucket size for grouping (e.g. `1d`).
        :param str nulls:
            How nulls should be handled (e.g. `omit`).
        """
        payload = {
            "m": metric,
            "from": start,
            "interval": interval,
            "nulls": nulls
        }
        return self._api_request("GET", "metrics/", payload)
