"""This is meant to be an extremely barebones auth implementation (with hardcoded users/passwords), for development purposes only."""

from ..definitions import USER

_MOCK_DB_FOR_NOW = {
    'admin': 'admin',
    'username': 'password',
}


def get_user(user_token: str) -> None | USER:
    password = _MOCK_DB_FOR_NOW.get(user_token)
    if password is None:
        return None
    return user_token, password
