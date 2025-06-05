import base64

import urllib3

from ...core.definitions import INTERSECT_MESSAGE_EXCHANGE
from ...core.environment import Settings
from ...core.log_config import logger
from ...utils.broker_credentials import get_broker_username, make_broker_password
from ...utils.client_name_generator import CLIENT_PREFIX
from . import AbstractBrokerHandler

RABBITMQ_VHOST = '%2F'
"""We use the same VHOST throughout RabbitMQ"""


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
            bytes(f'{settings.BROKER_ROOT_USERNAME}:{settings.BROKER_ROOT_PASSWORD}', 'utf-8')
        ).decode()
        self.base_headers = {
            'Authorization': f'Basic {basic_auth}',
        }
        self.http_client = urllib3.PoolManager(
            headers=self.base_headers,
        )

    def initialize_broker(self, client_username: str, client_password: str) -> None:
        """TODO - this should happen entirely on the BROKER

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
            body = rf'{{"exchange":"{INTERSECT_MESSAGE_EXCHANGE}","configure":"^$","write":"^({self.system_name}\\.{CLIENT_PREFIX}.*|.*\\.request|.*\\.response)$","read":"^({self.system_name}\\.{CLIENT_PREFIX}.*|.*\\.events)$"}}'
            resp = self.http_client.request(
                'PUT',
                f'{self._base_url}api/topic-permissions/{RABBITMQ_VHOST}/{client_username}',
                body,
                headers={**self.base_headers, 'Content-Type': 'application/json'},
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
            body = rf'{{"exchange":"{INTERSECT_MESSAGE_EXCHANGE}","configure":"^$","write":"^({self.system_name}\\.{service_name}\\..*|.*\\.request|.*\\.response)$","read":"^({self.system_name}\\.{service_name}\\..*|.*\\.events)$"}}'
            resp = self.http_client.request(
                'PUT',
                f'{self._base_url}api/topic-permissions/{RABBITMQ_VHOST}/{username}',
                body,
                headers={**self.base_headers, 'Content-Type': 'application/json'},
            )
            logger.debug('%s %s %s', resp.status, resp.headers, resp.data)
            if resp.status >= 400:
                msg = f'Could not set permissions for the service broker user {service_name}'
                logger.error('%s %s %s %s', msg, resp.status, resp.headers, resp.data)
                raise Exception(msg)  # noqa: TRY002
        else:
            # TODO figure out how things are generated on the MQTT side
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
