"""Logic for generating broker credentials.

Users are not able to generate these credentials themselves, and the registry service will regularly rotate these credentials.
"""

import secrets

_API_KEY_ENTROPY = 32


def get_broker_username(service_name: str) -> str:
    return f'{service_name}_user'


def make_broker_password() -> str:
    return secrets.token_urlsafe(_API_KEY_ENTROPY)
