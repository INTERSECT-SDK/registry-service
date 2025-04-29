from typing import Protocol

from ...core.environment import Settings


class AbstractProtocolHandler(Protocol):
    def initialize_broker(self) -> None:
        """TODO - this should happen entirely on the BROKER"""
        ...

    def initialize_service_config(self, service_name: str) -> None: ...

    def remove_service_config(self, service_name: str) -> None: ...


def get_protocol_handler(settings: Settings) -> AbstractProtocolHandler:
    match settings.BROKER_PROTOCOL:
        case 'amqp0.9.1':
            from .amqp0_9_1 import Amqp091ProtocolHander

            return Amqp091ProtocolHander(settings)
        case 'mqtt5.0':
            from .mqtt5_0 import Mqtt5ProtocolHandler

            return Mqtt5ProtocolHandler(settings)
        case _:
            # should never be reachable
            raise ValueError
