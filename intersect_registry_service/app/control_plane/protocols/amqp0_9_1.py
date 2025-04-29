from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pika

from ...core.definitions import (
    INTERSECT_MESSAGE_EXCHANGE,
    INTERSECT_SERVICE_SUBSCRIPTION_TYPES,
)
from ...core.environment import Settings
from ...core.log_config import logger
from . import AbstractProtocolHandler

if TYPE_CHECKING:
    from pika.frame import Frame


class Amqp091ProtocolHander(AbstractProtocolHandler):
    """This class handles any operations which should be handled through the AMQP protocol.

    IMPORTANT READING so you understand how permissions work: https://www.rabbitmq.com/docs/access-control#authorisation

    In general, this class should assume that:
      - Connections should be temporary - we do not actually engage in pub-sub operations with this core service, just configuration.
      - Connections should be blocking - a failure to execute a command generally means that there's a networking or durability failure somewhere.

    The way we handle exchanges:
      - We just use one exchange for everything. INTERSECT-SDK users should never modify this exchange themselves (though they are welcome to use `passive=True`)

    The way we handle queues:
      - Services will create their initial request/response queues
      - Each new queue will need to
    """

    def __init__(self, settings: Settings) -> None:
        self.system_name = settings.SYSTEM_NAME
        if settings.BROKER_TLS_CERT:
            import ssl

            context = ssl.create_default_context(
                cafile='/Users/me/tls-gen/basic/result/ca_certificate.pem'
            )
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_cert_chain(
                '/Users/me/tls-gen/result/client_certificate.pem',
                '/Users/me/tls-gen/result/client_key.pem',
            )
            ssl_options = pika.SSLOptions(context, settings.BROKER_HOST)
        else:
            ssl_options = None

        self._connection_params = pika.ConnectionParameters(
            host=settings.BROKER_HOST,
            port=settings.BROKER_PORT,
            virtual_host='/',
            credentials=pika.PlainCredentials(
                settings.BROKER_ROOT_USERNAME, settings.BROKER_ROOT_PASSWORD
            ),
            connection_attempts=3,
            ssl_options=ssl_options,
        )
        self.initialize_broker()

    def initialize_broker(self) -> None:
        """
        On initialization, we will need to:
          - create the main INTERSECT message exchange if it does not already exist.
          - initialize the Client user (this is done through the specific broker implementation, not the protocol)

        TODO - this should happen ENTIRELY on the BROKER side, not here
        """
        with pika.BlockingConnection(self._connection_params) as connection:
            channel = connection.channel()
            frame: Frame = channel.exchange_declare(
                exchange=INTERSECT_MESSAGE_EXCHANGE,
                exchange_type='topic',
                durable=True,
            )
            logger.info('amqp exchange declare result: %s', frame.method)

    def initialize_service_config(self, service_name: str) -> None:
        """
        On initialization, we will need to create a new queue and bind it to our exchange.
        """
        routing_key = f'{self.system_name}.{service_name}'
        with ThreadPoolExecutor(max_workers=2) as executor:
            for message_type in INTERSECT_SERVICE_SUBSCRIPTION_TYPES:
                executor.submit(
                    self._create_service_queues,
                    f'{routing_key}.{message_type}',
                    f'{service_name}_{message_type}',
                )

    def _create_service_queues(self, routing_key: str, queue_name: str) -> None:
        with pika.BlockingConnection(self._connection_params) as connection:
            channel = connection.channel()
            declare_frame: Frame = channel.queue_declare(
                queue_name,
                durable=True,
            )
            logger.info('declare_frame %s', declare_frame)
            actual_queue_name: str = declare_frame.method.queue
            bind_frame: Frame = channel.queue_bind(
                queue=actual_queue_name,
                exchange=INTERSECT_MESSAGE_EXCHANGE,
                routing_key=routing_key,
            )
            logger.info('bind_frame %s', bind_frame)

    def remove_service_config(self, service_name: str) -> None:
        with pika.BlockingConnection(self._connection_params) as connection:
            channel = connection.channel()
            for message_type in INTERSECT_SERVICE_SUBSCRIPTION_TYPES:
                remove_frame: Frame = channel.queue_delete(f'{service_name}_{message_type}')
                logger.info('remove_frame %s', remove_frame)
