"""This is meant to be an extremely barebones auth implementation (with hardcoded users/passwords), to be replaced by a combination of a DB and Keycloak."""

from ..user import USER

_MOCK_DB_FOR_NOW = {
    'admin': 'admin',
    'username': 'password',
}


def get_user_impl(username: str) -> None | USER:
    password = _MOCK_DB_FOR_NOW.get(username)
    if password is None:
        return None
    return username, password
