import ssl
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pika

from ...core.definitions import (
    INTERSECT_MESSAGE_EXCHANGE,
    INTERSECT_MESSAGE_TYPE,
    INTERSECT_MESSAGE_TYPES,
)
from ...core.environment import Settings
from ...core.log_config import logger
from ..get_queue_name import get_queue_name
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
      - We just use one exchange and virtual hosts for everything. INTERSECT-SDK users should never modify this exchange themselves (though they are welcome to use `passive=True`)

    The way we handle queues:
      - The registry service will create the initial request/response/event queues for services
    """

    def __init__(self, settings: Settings) -> None:
        self.system_name = settings.SYSTEM_NAME
        if settings.BROKER_TLS_CERT:
            ssl_options = pika.SSLOptions(context=ssl.create_default_context())
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
        with (
            ThreadPoolExecutor(max_workers=3) as executor,
        ):
            for message_type in INTERSECT_MESSAGE_TYPES:
                connection = pika.BlockingConnection(self._connection_params)
                executor.submit(
                    self._create_service_queues,
                    connection,
                    service_name,
                    message_type,
                )

    def _create_service_queues(
        self,
        connection: pika.BlockingConnection,
        service_name: str,
        message_type: INTERSECT_MESSAGE_TYPE,
    ) -> None:
        queue_name = get_queue_name(service_name, True, message_type)
        channel = connection.channel()
        declare_frame: Frame = channel.queue_declare(
            queue_name,
            durable=True,
        )
        logger.info('declare_frame %s', declare_frame)
        # TODO - maybe leave all binding up to the INTERSECT SDK microservice
        # events need to be dynamically bound/unbound by the services themselves
        if message_type != 'events':
            actual_queue_name: str = declare_frame.method.queue
            bind_frame: Frame = channel.queue_bind(
                queue=actual_queue_name,
                exchange=INTERSECT_MESSAGE_EXCHANGE,
                routing_key=f'{self.system_name}.{service_name}.{message_type}.#',
            )
            logger.info('bind_frame %s', bind_frame)

    def remove_service_config(self, service_name: str) -> None:
        with pika.BlockingConnection(self._connection_params) as connection:
            channel = connection.channel()
            for message_type in INTERSECT_MESSAGE_TYPES:
                remove_frame: Frame = channel.queue_delete(
                    get_queue_name(service_name, True, message_type)
                )
                logger.info('remove_frame %s', remove_frame)
