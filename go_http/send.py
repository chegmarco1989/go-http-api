""" Simple utilities for sending messages via Vumi Go' HTTP API.
"""

import json
import logging
import pprint
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
        ``https://go.vumi.org/api/v1/go/http_api_nostream``.
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
            api_url = "https://go.vumi.org/api/v1/go/http_api_nostream"
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

    def _raw_send(self, data):
        try:
            return self._api_request('messages.json', data)
        except HTTPError as e:
            try:
                response = e.response.json()
            except ValueError:  # Some HTTP responses are not decodable
                raise e
            if (e.response.status_code != 400 or
                    'opted out' not in response.get('reason', '') or
                    response.get('success')):
                raise e
            raise UserOptedOutException(
                data.get("to_addr"), data.get("content"),
                response.get('reason'))

    def send_text(self, to_addr, content, session_event=None):
        """ Send a text message to an address.

        :param str to_addr:
            Address to send to.
        :param str content:
            Text to send.
        :param str session_event:
            The session event for session-based messaging channels (e.g. USSD).
            May be one of 'new', 'resume' or 'close'. Optional.
        """
        data = {
            "to_addr": to_addr,
            "content": content,
        }
        if session_event is not None:
            data["session_event"] = session_event
        return self._raw_send(data)

    def send_voice(self, to_addr, content, speech_url=None, wait_for=None,
                   session_event=None):
        """ Send a voice message to an address.

        :param str to_addr:
            Address to send to.
        :param str content:
            Text to send. If ``speech_url`` is not provided, a text-to-speech
            engine is used to generate a voice message from this text. If
            ``speech_url`` is provided, this text is ignored by voice
            messaging channels, but may still be used by non-voice channels
            that process the message.
        :param str speech_url:
            A URL to a voice file containing the voice message to sent.
            If not given, a voice message is generated from ``content`` using
            a text-to-speech engine. Optional.
        :param str wait_for:
            By default the Vumi voice connections send a response to a
            message as soon as a key is pressed by the person the call is with.
            The ``wait_for`` option allows specifying a character to wait for
            before a response is returned. For example, without ``wait_for``
            pressing '123#' on the phone would result in four response messages
            containing '1', '2', '3' and '#' respectively. If
            ``wait_for='#'`` was set, pressing '123#' would result in a
            single response message containing '123'. Optional.
        :param str session_event:
            The session event. May be one of 'new', 'resume' or 'close'.
            'new' initiates a new call. 'resume' continues an existing call.
            'close' ends an existing call. The default of ``None`` is
            equivalent to 'resume'.
        """
        data = {
            "to_addr": to_addr,
            "content": content,
        }
        if session_event is not None:
            data["session_event"] = session_event
        voice = {}
        if speech_url is not None:
            voice["speech_url"] = speech_url
        if wait_for is not None:
            voice["wait_for"] = wait_for
        if voice:
            data["helper_metadata"] = {"voice": voice}
        return self._raw_send(data)

    def fire_metric(self, metric, value, agg="last"):
        """ Fire a value for a metric.

        :param str metric:
            Name of the metric to fire.
        :param float value:
            Value for the metric.
        :param str agg:
            Aggregation type. Defaults to ``'last'``. Other allowed values are
            ``'sum'``, ``'avg'``, ``'max'`` and ``'min'``.

        Note that metrics can also be fired via the metrics API.
        See :meth:`go_http.metrics.MetricsApiClient.fire`.
        """
        data = [
            [
                metric,
                value,
                agg
            ]
        ]
        return self._api_request('metrics.json', data)


class LoggingSender(HttpApiSender):
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

    def _api_request(self, suffix, py_data):
        if suffix == "messages.json":
            return self._handle_messages(py_data)
        elif suffix == "metrics.json":
            return self._handle_metrics(py_data)
        else:
            raise ValueError("XXX")

    def _handle_messages(self, data):
        data["message_id"] = uuid.uuid4().hex
        msg = "Message: %r sent to %r" % (data['content'], data['to_addr'])
        if data.get("session_event"):
            msg += " [session_event: %s]" % data["session_event"]
        if data.get("helper_metadata"):
            for key, value in sorted(data["helper_metadata"].items()):
                msg += " [%s: %s]" % (key, pprint.pformat(value))
        self._logger.log(self._level, msg)
        return data

    def _handle_metrics(self, data):
        for metric, value, agg in data:
            assert agg in ["last", "sum", "avg", "max", "min"]
            self._logger.log(
                self._level, "Metric: %r [%s] -> %g" % (
                    metric, agg, float(value),
                ))
        return {
            "success": True,
            "reason": "Metrics published",
        }
