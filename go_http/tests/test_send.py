""" Tests for go_http.send. """

import json
import logging
from unittest import TestCase

from requests_testadapter import TestAdapter, TestSession

from go_http.send import HttpApiSender, LoggingSender
from go_http.exceptions import UserOptedOutException

from requests.exceptions import HTTPError


class RecordingAdapter(TestAdapter):
    """ Record the request that was handled by the adapter.
    """
    request = None

    def send(self, request, *args, **kw):
        self.request = request
        return super(RecordingAdapter, self).send(request, *args, **kw)


class TestHttpApiSender(TestCase):

    def setUp(self):
        self.session = TestSession()
        self.sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            api_url="http://example.com/api/v1/go/http_api_nostream",
            conversation_token="conv-token", session=self.session)

    def test_default_session(self):
        import requests
        sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            conversation_token="conv-token")
        self.assertTrue(isinstance(sender.session, requests.Session))

    def test_default_api_url(self):
        sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            conversation_token="conv-token")
        self.assertEqual(sender.api_url,
                         "https://go.vumi.org/api/v1/go/http_api_nostream")

    def check_request(self, request, method, data=None, headers=None):
        self.assertEqual(request.method, method)
        if data is not None:
            self.assertEqual(json.loads(request.body), data)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)

    def check_successful_send(self, send, expected_data):
        adapter = RecordingAdapter(json.dumps({"message_id": "id-1"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "messages.json", adapter)
        result = send()
        self.assertEqual(result, {
            "message_id": "id-1",
        })
        self.check_request(
            adapter.request, 'PUT', data=expected_data,
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})

    def test_send_text(self):
        self.check_successful_send(
            lambda: self.sender.send_text("to-addr-1", "Hello!"),
            {
                "content": "Hello!", "to_addr": "to-addr-1",
            })

    def test_send_text_with_session_event(self):
        self.check_successful_send(
            lambda: self.sender.send_text(
                "to-addr-1", "Hello!", session_event="close"),
            {
                "content": "Hello!", "to_addr": "to-addr-1",
                "session_event": "close",
            })

    def test_send_text_to_opted_out(self):
        """
        UserOptedOutException raised for sending messages to opted out
        recipients
        """
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "messages.json", TestAdapter(
                json.dumps({
                    "success": False,
                    "reason": "Recipient with msisdn to-addr-1 has opted out"}
                ),
                status=400))
        try:
            self.sender.send_text('to-addr-1', "foo")
        except UserOptedOutException as e:
            self.assertEqual(e.to_addr, 'to-addr-1')
            self.assertEqual(e.message, 'foo')
            self.assertEqual(
                e.reason, 'Recipient with msisdn to-addr-1 has opted out')

    def test_send_text_to_other_http_error(self):
        """
        HTTP errors should not be raised as UserOptedOutExceptions if they are
        not user opted out errors.
        """
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "messages.json", TestAdapter(
                json.dumps({
                    "success": False,
                    "reason": "No unicorns were found"
                }),
                status=400))
        try:
            self.sender.send_text('to-addr-1', 'foo')
        except HTTPError as e:
            self.assertEqual(e.response.status_code, 400)
            response = e.response.json()
            self.assertFalse(response['success'])
            self.assertEqual(response['reason'], "No unicorns were found")

    def test_send_text_to_other_http_error_not_json(self):
        """
        HTTP errors that are not json encode should be raised without decoding
        errors
        """
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "messages.json", TestAdapter(
                "401 Client Error: Unauthorized",
                status=401))
        try:
            self.sender.send_text('to-addr-1', 'foo')
        except HTTPError as e:
            self.assertEqual(e.response.status_code, 401)
            self.assertEqual(e.response.text,
                             "401 Client Error: Unauthorized")

    def test_send_voice(self):
        self.check_successful_send(
            lambda: self.sender.send_voice("to-addr-1", "Hello!"),
            {
                "content": "Hello!", "to_addr": "to-addr-1",
            })

    def test_send_voice_with_session_event(self):
        self.check_successful_send(
            lambda: self.sender.send_voice(
                "to-addr-1", "Hello!", session_event="close"),
            {
                "content": "Hello!", "to_addr": "to-addr-1",
                "session_event": "close",
            })

    def test_send_voice_with_speech_url(self):
        self.check_successful_send(
            lambda: self.sender.send_voice(
                "to-addr-1", "Hello!",
                speech_url="http://example.com/voice.ogg"),
            {
                "content": "Hello!", "to_addr": "to-addr-1",
                "helper_metadata": {
                    "voice": {"speech_url": "http://example.com/voice.ogg"},
                },
            })

    def test_send_voice_with_wait_for(self):
        self.check_successful_send(
            lambda: self.sender.send_voice(
                "to-addr-1", "Hello!", wait_for="#"),
            {
                "content": "Hello!", "to_addr": "to-addr-1",
                "helper_metadata": {
                    "voice": {"wait_for": "#"},
                },
            })

    def test_fire_metric(self):
        adapter = RecordingAdapter(
            json.dumps({"success": True, "reason": "Yay"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "metrics.json", adapter)

        result = self.sender.fire_metric("metric-1", 5.1, agg="max")
        self.assertEqual(result, {
            "success": True,
            "reason": "Yay",
        })
        self.check_request(
            adapter.request, 'PUT',
            data=[["metric-1", 5.1, "max"]],
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})

    def test_fire_metric_default_agg(self):
        adapter = RecordingAdapter(
            json.dumps({"success": True, "reason": "Yay"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "metrics.json", adapter)

        result = self.sender.fire_metric("metric-1", 5.2)
        self.assertEqual(result, {
            "success": True,
            "reason": "Yay",
        })
        self.check_request(
            adapter.request, 'PUT',
            data=[["metric-1", 5.2, "last"]],
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})


class RecordingHandler(logging.Handler):
    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class TestLoggingSender(TestCase):

    def setUp(self):
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg, levelno=logging.INFO):
        [log] = self.handler.logs
        self.assertEqual(log.msg, msg)
        self.assertEqual(log.levelno, levelno)

    def test_send_text(self):
        result = self.sender.send_text("to-addr-1", "Hello!")
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
        })
        self.check_logs("Message: 'Hello!' sent to 'to-addr-1'")

    def test_send_text_with_session_event(self):
        result = self.sender.send_text(
            "to-addr-1", "Hello!", session_event='close')
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
            "session_event": "close",
        })
        self.check_logs(
            "Message: 'Hello!' sent to 'to-addr-1'"
            " [session_event: close]")

    def test_send_voice(self):
        result = self.sender.send_voice("to-addr-1", "Hello!")
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
        })
        self.check_logs("Message: 'Hello!' sent to 'to-addr-1'")

    def test_send_voice_with_session_event(self):
        result = self.sender.send_voice(
            "to-addr-1", "Hello!", session_event='close')
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
            "session_event": "close",
        })
        self.check_logs(
            "Message: 'Hello!' sent to 'to-addr-1'"
            " [session_event: close]")

    def test_send_voice_with_speech_url(self):
        result = self.sender.send_voice(
            "to-addr-1", "Hello!", speech_url='http://example.com/voice.ogg')
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
            "helper_metadata": {
                "voice": {
                    "speech_url": "http://example.com/voice.ogg",
                },
            }
        })
        self.check_logs(
            "Message: 'Hello!' sent to 'to-addr-1'"
            " [voice: {'speech_url': 'http://example.com/voice.ogg'}]")

    def test_send_voice_with_wait_for(self):
        result = self.sender.send_voice(
            "to-addr-1", "Hello!", wait_for="#")
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
            "helper_metadata": {
                "voice": {
                    "wait_for": "#",
                },
            }
        })
        self.check_logs(
            "Message: 'Hello!' sent to 'to-addr-1'"
            " [voice: {'wait_for': '#'}]")

    def test_fire_metric(self):
        result = self.sender.fire_metric("metric-1", 5.1, agg="max")
        self.assertEqual(result, {
            "success": True,
            "reason": "Metrics published",
        })
        self.check_logs("Metric: 'metric-1' [max] -> 5.1")

    def test_fire_metric_default_agg(self):
        result = self.sender.fire_metric("metric-1", 5.2)
        self.assertEqual(result, {
            "success": True,
            "reason": "Metrics published",
        })
        self.check_logs("Metric: 'metric-1' [last] -> 5.2")
