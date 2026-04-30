"""Logic for getting queue names of brokers"""

from ..core.definitions import INTERSECT_MESSAGE_TYPE


def get_queue_name_prefix(service_or_client_name: str, is_service: bool) -> str:
    # clients already have the prefix in their name
    prefix = 'SVC_' if is_service else ''
    return f'{prefix}{service_or_client_name}-'


def get_queue_name(
    service_or_client_name: str,
    is_service: bool,
    message_type: INTERSECT_MESSAGE_TYPE,
) -> str:
    return f'{get_queue_name_prefix(service_or_client_name, is_service)}{message_type}'
