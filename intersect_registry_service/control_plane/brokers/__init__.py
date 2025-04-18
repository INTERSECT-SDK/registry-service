from typing import Protocol

from ...core.environment import Settings


class AbstractBrokerHandler(Protocol):
    """
    We do certain tasks based on the broker we're using, not the protocol specifically.

    The broker implementation determines:
      - how we create microservice users
      - how we add permissions to these users
    """

    def initialize_broker(self, client_username: str, client_password: str) -> None:
        """TODO - this should happen entirely on the BROKER"""
        ...

    def initialize_service_config(self, service_name: str) -> tuple[str, str]: ...

    def remove_service_config(self, service_name: str) -> None: ...


def get_broker_handler(settings: Settings) -> AbstractBrokerHandler:
    match settings.BROKER_APPLICATION:
        case 'rabbitmq':
            from .rabbitmq import RabbitMQHandler

            return RabbitMQHandler(settings)
        case _:
            # should never be reachable
            raise ValueError
