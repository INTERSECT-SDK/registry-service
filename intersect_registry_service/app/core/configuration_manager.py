from ..control_plane.brokers import get_broker_handler
from ..control_plane.protocols import get_protocol_handler
from ..core.environment import Settings


class ConfigurationManager:
    """API to handle configuration of INTERSECT as a whole."""

    def __init__(self, settings: Settings) -> None:
        self.protocol_handler = get_protocol_handler(settings)
        self.broker_handler = get_broker_handler(settings)

    def initialize_broker(self, settings: Settings) -> None:
        self.protocol_handler.initialize_broker()
        self.broker_handler.initialize_broker(
            settings.BROKER_CLIENT_USERNAME, settings.BROKER_CLIENT_PASSWORD
        )

    def add_service(self, service_name: str) -> tuple[str, str]:
        """Returns: generated username and password for the broker, to be used with that service"""
        self.protocol_handler.initialize_service_config(service_name)
        return self.broker_handler.initialize_service_config(service_name)

    def update_service(self, service_name: str, automatic_update: bool) -> str:
        """Returns: the updated password the broker should use"""
        return self.broker_handler.update_service_config(service_name, automatic_update)
