from ...core.environment import Settings
from . import AbstractProtocolHandler


class Mqtt5ProtocolHandler(AbstractProtocolHandler):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.initialize_broker()

    def initialize_broker(self) -> None:
        raise NotImplementedError

    def initialize_service_config(self, service_name: str) -> None:
        raise NotImplementedError

    def remove_service_config(self, service_name: str) -> None:
        raise NotImplementedError
