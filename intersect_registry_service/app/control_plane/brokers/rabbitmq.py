"""
Search https://github.com/rabbitmq/rabbitmq-server/blob/b1f3d4bc3683fbb2964a5472f5efcb31839e80a0/deps/rabbit/src/rabbit_channel.erl
specifically (check_read check_write check_config) functions

Permissions here only apply for dynamically added microservices, core services may or may not have additional permissions.

URI logic is:

{SYSTEM}.{SERVICE}.{events|request|response|lifecycle}.{OTHER_ADDITIONAL_INFORMATION}

- SYSTEM = anything attached to this broker
- SERVICE = A namespace of a microservice in the system, reserved by the registry service
- MESSAGE_TYPE = one of {events, request, response, lifecycle}
- The INTERSECT-SDK suffix marked by {OTHER_ADDITIONAL_INFORMATION} may change, this is not important to the registry service

SYSTEM and SERVICE are enough to actually form a unique URI to a given microservice.
MESSAGE_TYPE is enough to determine how a message can be handled.

Rules:
    - everything uses the same exchange (may change this for MQTT)
    - configuration is always done on the Registry Service
    - {SYSTEM}.{SERVICE} is a sufficient URI to a given microservice
    - Anyone can write to a Service or Client's request/response channel, but only that entity may read it.
    - Anyone can read a Service's events channel, but only that Service may write to it.
"""

import base64
import json

import urllib3

from ...core.definitions import (
    INTERSECT_MESSAGE_EXCHANGE,
    INTERSECT_MESSAGE_TYPES,
)
from ...core.environment import Settings
from ...core.log_config import logger
from ...utils.broker_credentials import (
    get_broker_username,
    make_broker_password,
)
from ...utils.client_name_generator import CLIENT_PREFIX
from ..get_queue_name import get_queue_name_prefix
from . import AbstractBrokerHandler

RABBITMQ_VHOST = '%2F'
"""We use the same VHOST throughout RabbitMQ"""

CLIENT_PERMISSIONS_REGEX = f'{CLIENT_PREFIX}[0-9a-f-]{{36}}'
"""This is a Client's 'service name', but they are dynamically and automatically generated at runtime."""


class RabbitMQHandler(AbstractBrokerHandler):
    """
    The RabbitMQ implementation works with the RabbitMQ Management REST API to configure users and permissions.

    For a reference, see https://www.rabbitmq.com/docs/http-api-reference

    Exchanges and Queues should be configured via the protocol.
    """

    def __init__(self, settings: Settings) -> None:
        if settings.BROKER_PROTOCOL not in ('amqp0.9.1', 'mqtt5.0'):
            msg = f'Cannot use protocol {settings.BROKER_PROTOCOL} with rabbitmq'
            raise Exception(msg)  # noqa: TRY002
        self.is_amqp = settings.BROKER_PROTOCOL == 'amqp0.9.1'
        """Topic Authorization will probably remain the same across all protocols, but AMQP uses the normal ACL layer differently (the other protocols generate names).

        See: https://www.rabbitmq.com/docs/access-control#topic-authorisation
        """
        self.system_name = settings.SYSTEM_NAME
        self._base_url = str(settings.BROKER_MANAGEMENT_URI)
        if self._base_url[-1] != '/':
            self._base_url += '/'
        basic_auth = base64.b64encode(
            bytes(
                f'{settings.BROKER_ROOT_USERNAME}:{settings.BROKER_ROOT_PASSWORD}',
                'utf-8',
            )
        ).decode()
        self.base_headers = {
            'Authorization': f'Basic {basic_auth}',
        }
        self.http_client = urllib3.PoolManager(
            headers=self.base_headers,
        )

    def initialize_broker(self, client_username: str, client_password: str) -> None:
        """TODO - this should happen entirely on the BROKER

        though it is nice to do it here so we don't have to modify the broker configuration

        Attempts to:
          - create the Client user
          - set permissions on the Client user

        This needs to be called AFTER the INTERSECT exchange is created.
        """
        resp = self.http_client.request(
            'PUT',
            f'{self._base_url}api/users/{client_username}',
            f'{{"password":"{client_password}","tags":[]}}',
            headers={**self.base_headers, 'Content-Type': 'application/json'},
        )
        if resp.status >= 400:
            msg = f'Could not initialize the client broker user {client_username}'
            logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
            raise Exception(msg)  # noqa: TRY002

        # CLIENT PERMISSIONS:
        # - limited to working with the INTERSECT message exchange
        # - not allowed to configure anything
        # - may write (publish) to any request/response channels
        # - may read (subscribe) from any event channel
        # - may write (publish) to your own event channel
        # - may read (subscribe) from your own request/response channels
        # - NOTE: clients can technically read and write to any channel of any other client, beware. WONTFIX because Clients should generally not be used in production.
        if self.is_amqp:
            body = self._get_rmq_permissions(CLIENT_PERMISSIONS_REGEX, False)

            ### permissions
            resp = self.http_client.request(
                'PUT',
                f'{self._base_url}api/permissions/{RABBITMQ_VHOST}/{client_username}',
                body,
                headers={
                    **self.base_headers,
                    'Content-Type': 'application/json',
                },
            )

            if resp.status >= 400:
                msg = (
                    f'Could not set topic permissions for the client broker user {client_username}'
                )
                logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
                raise Exception(msg)  # noqa: TRY002

            ### topic permissions
            body = self._get_rmq_topic_permissions(CLIENT_PERMISSIONS_REGEX)
            resp = self.http_client.request(
                'PUT',
                f'{self._base_url}api/topic-permissions/{RABBITMQ_VHOST}/{client_username}',
                body,
                headers={
                    **self.base_headers,
                    'Content-Type': 'application/json',
                },
            )

            if resp.status >= 400:
                msg = (
                    f'Could not set topic permissions for the client broker user {client_username}'
                )
                logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
                raise Exception(msg)  # noqa: TRY002
        else:
            # TODO figure out how things are generated on the MQTT side
            raise NotImplementedError

    def initialize_service_config(self, service_name: str) -> tuple[str, str]:
        """
        Assume that we will only call this when:
          - We create a new Service
          - We need to rotate the broker credentials around

        For now:
        - the username is the same as the service name, but with a suffix appended to it (this cannot be duplicated when creating a Service name)
        - the password is randomly generated (and is URI safe)

        This returns the username and password.
        """
        username = get_broker_username(service_name)
        password = make_broker_password()
        resp = self.http_client.request(
            'PUT',
            f'{self._base_url}api/users/{username}',
            f'{{"password":"{password}","tags":[]}}',
        )
        logger.debug('%s %s %s', resp.status, resp.headers, resp.data)
        if resp.status >= 400:
            msg = f'Could not initialize the service broker user for {service_name}'
            logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
            raise Exception(msg)  # noqa: TRY002

        if self.is_amqp:
            # SERVICE PERMISSIONS:
            # - limited to working with the INTERSECT message exchange
            # - not allowed to configure anything
            # - may write (publish) to any request/response channels (TODO may want to restrict this to specific endpoints through OAuth scopes determined by Service user later)
            # - may read (subscribe) from any event channel (TODO may want to restrict this to specific events through OAuth scopes determined by Service user later)
            # - may read/write to any of your own channels
            body = self._get_rmq_permissions(service_name, True)

            # permissions

            resp = self.http_client.request(
                'PUT',
                f'{self._base_url}api/permissions/{RABBITMQ_VHOST}/{username}',
                body,
                headers={
                    **self.base_headers,
                    'Content-Type': 'application/json',
                },
            )
            logger.debug('%s %s %s', resp.status, resp.headers, resp.data)
            if resp.status >= 400:
                msg = f'Could not set topic permissions for the service broker user {service_name}'
                logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
                raise Exception(msg)  # noqa: TRY002

            ### topic permissions
            body = self._get_rmq_topic_permissions(service_name)
            resp = self.http_client.request(
                'PUT',
                f'{self._base_url}api/topic-permissions/{RABBITMQ_VHOST}/{username}',
                body,
                headers={
                    **self.base_headers,
                    'Content-Type': 'application/json',
                },
            )
            logger.debug('%s %s %s', resp.status, resp.headers, resp.data)
            if resp.status >= 400:
                msg = f'Could not set topic permissions for the service broker user {service_name}'
                logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
                raise Exception(msg)  # noqa: TRY002
        else:
            # TODO figure out how things are generated on the MQTT side, looks like it's just a matter of tweaking queue names and exchanges
            raise NotImplementedError

        return username, password

    def remove_service_config(self, service_name: str) -> None:
        """This just removes the username, we need to delete the service queue elsewhere (should be faster to do this via AMQP)"""
        username = get_broker_username(service_name)
        resp = self.http_client.request(
            'DELETE',
            f'{self._base_url}api/users/{username}',
        )
        if resp.status >= 400:
            msg = f'Could not delete the broker user for service {service_name}'
            raise Exception(msg)  # noqa: TRY002

    def _get_rmq_permissions(self, service_or_prefix: str, is_service: bool) -> str:
        """Note contrast to TOPIC permissions

        The name regex matches the names of the queues.

        Configure: COMPLETELY disabled, as it would only used for:
            - non-passive exchange.declare
            - non-passive queue.declare
            - queue.delete
            - exchange.delete
        These are always managed by the Registry Service.

        Write: allow all by default (keep in mind: this is writing to OTHER queues).
        Read: your queues only
        """
        regex_prefix = get_queue_name_prefix(service_or_prefix, is_service)
        body = {
            'configure': '^$',
            'write': '.*',
            'read': f'^{regex_prefix}({"|".join(INTERSECT_MESSAGE_TYPES)})',
        }
        return json.dumps(body)

    def _get_rmq_topic_permissions(self, service_or_prefix: str) -> str:
        """Note contrast to regular permissions

        These are meant to restrict the allowed topics which can be posted on.
        We only care about the prefixes for now, topic suffixes are deliberately left extensible.
        (For example, events also have a {capability}/{event_name} syntax tree, but this is not the concern of authorization.)

        Exchange: self-explanatory, don't send messages to non-INTERSECT services
        TOPIC read: You can subscribe to your own request/response messages, and are allowed to subscribe to any event.
        TOPIC write: You can publish your own event messages, and can publish to any request/response channel.
        """
        body = {
            'exchange': INTERSECT_MESSAGE_EXCHANGE,
            'write': (
                rf'^({self.system_name}\\.{service_or_prefix}\\.events\\.?)'
                r'|([a-z0-9-]+\\.[a-z0-9-]+\\.(request|response)\\.?)'
            ),
            'read': (
                rf'^({self.system_name}\\.{service_or_prefix}\\.(request|response)\\.?)'
                r'|([a-z0-9-]+\\.[a-z0-9-]+\\.events\\.?)'
            ),
        }
        return json.dumps(body)
