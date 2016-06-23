"""Fixtures for the account API."""

import copy

campaigns = [{
    u'name': u'Your Campaign',
    u'key': u'key-hash-1',
}]

channels = [{
    u'endpoints': [{
        u'uuid': u'TRANSPORT_TAG:tagpool:tagname::default',
        u'name': u'default',
    }],
    u'tag': [u'tagpool', u'tagname'],
    u'description': u'Tagpool: Tagname',
    u'name': u'A nice name',
    u'uuid': u'channel-uuid-1',
}]

conversations = [{
    u'type': u'dialogue',
    u'status': u'running',
    u'uuid': u'conv-1',
    u'name': u'Test Dialogue',
    u'endpoints': [{
        u'uuid': u'CONVERSATION:dialogue:conv-1::default',
        u'name': u'default',
    }],
    u'description': u'Small dialogue for testing'
}]

routers = [{
    u'status': u'running',
    u'description': u'Keyword router for my app',
    u'conversation_endpoints': [{
        u'uuid': u'ROUTER:keyword:rtr-1:OUTBOUND::default',
        u'name': u'default',
    }, {
        u'uuid': u'ROUTER:keyword:rtr-1:OUTBOUND::keyword_two',
        u'name': u'keyword_two',
    }, {
        u'uuid': u'ROUTER:keyword:rtr-1:OUTBOUND::keyword_one',
        u'name': u'keyword_one',
    }],
    u'uuid': u'rtr-1',
    u'channel_endpoints': [{
        u'uuid': u'ROUTER:keyword:rtr-1:INBOUND::default',
        u'name': u'default',
    }],
    u'type': u'keyword',
    u'name': u'Keywords for my app',
}]

routing_entries = [{
    u'source': {
        u'uuid': u'TRANSPORT_TAG:tagpool:tagname::default',
    },
    u'target': {
        u'uuid': u'CONVERSATION:conv_type:conv-id-1::default',
    },
}]

routing_table = copy.deepcopy({
    u'channels': channels,
    u'conversations': conversations,
    u'routers': routers,
    u'routing_entries': routing_entries,
})
