""" Simple utilities for sending messages via Vumi Go' HTTP API.
"""

import json
import logging
import uuid

import requests
from requests.exceptions import HTTPError

from go_http.exceptions import UserOptedOutException


class HttpApiSender(object):
    """
    A helper for sending text messages and firing metrics via Vumi Go's HTTP
    API.

    :param str account_key:
        The unique id of the account to send to.
        You can find this at the bottom of the Account > Details
        page in Vumi Go.
    :param str conversation_key:
        The unique id of the conversation to send to.
        This is the UUID at the end of the conversation URL.
    :param str conversation_token:
        The secret authentication token entered in the
        conversation config.
    :param str api_url:
        The full URL of the HTTP API. Defaults to
        ``http://go.vumi.org/api/v1/go/http_api_nostream``.
    :type session:
        :class:`requests.Session`
    :param session:
        Requests session to use for HTTP requests. Defaults to
        a new session.
    """

    def __init__(self, account_key, conversation_key, conversation_token,
                 api_url=None, session=None):
        self.account_key = account_key
        self.conversation_key = conversation_key
        self.conversation_token = conversation_token
        if api_url is None:
            api_url = "http://go.vumi.org/api/v1/go/http_api_nostream"
        self.api_url = api_url
        if session is None:
            session = requests.Session()
        self.session = session

    def _api_request(self, suffix, py_data):
        url = "%s/%s/%s" % (self.api_url, self.conversation_key, suffix)
        headers = {'content-type': 'application/json; charset=utf-8'}
        auth = (self.account_key, self.conversation_token)
        data = json.dumps(py_data)
        r = self.session.put(url, auth=auth, data=data, headers=headers)
        r.raise_for_status()
        return r.json()

    def send_text(self, to_addr, content):
        """ Send a message to an address.

        :param str to_addr:
            Address to send to.
        :param str content:
            Text to send.
        """
        data = {
            "content": content,
            "to_addr": to_addr,
        }
        try:
            return self._api_request('messages.json', data)
        except HTTPError as e:
            response = e.response.json()
            if (
                    e.response.status_code != 400 or
                    'opted out' not in response.get('reason', '') or
                    response.get('success')):
                raise e
            raise UserOptedOutException(
                to_addr, content, response.get('reason'))

    def fire_metric(self, metric, value, agg="last"):
        """ Fire a value for a metric.

        :param str metric:
            Name of the metric to fire.
        :param float value:
            Value for the metric.
        :param str agg:
            Aggregation type. Defaults to ``'last'``. Other allowed values are
            ``'sum'``, ``'avg'``, ``'max'`` and ``'min'``.
        """
        data = [
            [
                metric,
                value,
                agg
            ]
        ]
        return self._api_request('metrics.json', data)


class LoggingSender(object):
    """
    A helper for pretending to sending text messages and fire metrics by
    instead logging them via Python's logging module.

    :param str logger:
        The name of the logger to use.
    :param int level:
        The level to log at. Defaults to ``logging.INFO``.
    """

    def __init__(self, logger, level=logging.INFO):
        self._logger = logging.getLogger(logger)
        self._level = level

    def send_text(self, to_addr, content):
        """ Send a message to an address.

        :param str to_addr:
            Address to send to.
        :param str content:
            Text to send.
        """
        self._logger.log(
            self._level, "Message: %r sent to %r" % (content, to_addr))
        return {
            "message_id": uuid.uuid4().hex,
            "content": content,
            "to_addr": to_addr,
        }

    def fire_metric(self, metric, value, agg="last"):
        """ Fire a value for a metric.

        :param str metric:
            Name of the metric to fire.
        :param float value:
            Value for the metric.
        :param str agg:
            Aggregation type. Defaults to ``'last'``. Other allowed values are
            ``'sum'``, ``'avg'``, ``'max'`` and ``'min'``.
        """
        assert agg in ["last", "sum", "avg", "max", "min"]
        self._logger.log(
            self._level, "Metric: %r [%s] -> %g" % (metric, agg, float(value)))
        return {
            "success": True,
            "reason": "Metrics published",
        }
