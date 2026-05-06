"""This module consists of core definitions which are meant to transcend the entire application"""

from typing import Literal, get_args

BrokerProtocol = Literal['amqp0.9.1', 'mqtt5.0']
"""PubSub protocols we support."""

BrokerApplication = Literal['rabbitmq']
"""Broker applications we support."""

INTERSECT_MESSAGE_EXCHANGE = 'intersect-messages'
"""Currently, this is just used for the name of the message exchange on RabbitMQ."""

INTERSECT_MESSAGE_TYPE = Literal['request', 'response', 'events']
"""A type of message sent by INTERSECT."""
# excluding Lifecycle Messages, those are only parsed by core services
INTERSECT_MESSAGE_TYPES = get_args(INTERSECT_MESSAGE_TYPE)
"""These are the types of messages sent by INTERSECT, each message type needs its own queue."""


def get_raw_protocol(proto: BrokerProtocol, tls: bool = False) -> str:
    """strip protocol version and handle TLS changes"""
    if proto == 'amqp0.9.1':
        return 'amqps' if tls else 'amqp'
    if proto == 'mqtt5.0':
        return 'mqtts' if tls else 'mqtt'
    msg = f'Unsupported proto {proto}'
    raise ValueError(msg)


def get_uri_path(proto: BrokerProtocol) -> str:
    if proto == 'amqp0.9.1':
        # use the '/' virtual host for every single message
        return '/%2F'
    if proto == 'mqtt5.0':
        # no path options
        return '/'
    msg = f'Unsupported proto {proto}'
    raise ValueError(msg)


HIERARCHY_REGEX = r'[a-z0-9][-a-z0-9]{2,62}'
"""Regex we permit for the System name (defined by us) and the Service names (requested by users)"""
