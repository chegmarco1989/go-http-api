""" Simple utilities for sending messages via Vumi Go' HTTP API.
"""

import json

import requests


class Sender(object):
    """
    A simple object for sending message via Vumi Go's HTTP API.

    :param str api_url:
        The full URL of the HTTP API.
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
    :type session:
        :class:`requests.Session`
    :param session:
        Requests session to use for HTTP requests. Defaults to
        a new session.
    """

    def __init__(self, api_url, account_key, conversation_key,
                 conversation_token, session=None):
        self.api_url = api_url
        self.account_key = account_key
        self.conversation_key = conversation_key
        self.conversation_token = conversation_token
        if session is None:
            session = requests.Session()
        self.session = session

    def send(self, to_addr, content):
        """ Send a message to an address.

        :param str to_addr:
            Address to send to.
        :param str content:
            Text to send.
        """
        url = "%s/%s/messages.json" % (self.api_url, self.conversation_key)
        auth = (self.account_key, self.conversation_token)
        data = json.dumps({
            "content": content,
            "to_addr": to_addr
        })
        r = self.session.put(url, auth=auth, data=data)
        r.raise_for_status()
        return r.json()
