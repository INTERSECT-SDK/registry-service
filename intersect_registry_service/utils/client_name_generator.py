from uuid import uuid4

CLIENT_PREFIX = 'CLIENT_'
"""This is a unique prefix which Services cannot reserve for themselves. This is used to construct the Client equivalent of the 'service_name' (for topic routing) and appropriate permissions."""


def generate_client_name() -> str:
    return f'{CLIENT_PREFIX}{uuid4()!s}'
