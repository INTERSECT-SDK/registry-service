"""We don't allow users to create their own API keys, use this logic to generate keys for the server.

We WILL allow users to choose whether or not they rotate their API keys, we won't routinely do this ourselves.
"""

import secrets

_API_KEY_ENTROPY = 32


def make_api_key() -> str:
    return secrets.token_urlsafe(_API_KEY_ENTROPY)
