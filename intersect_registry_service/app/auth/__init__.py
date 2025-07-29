"""
Note that this authentication should ONLY apply to the UI-facing side. INTERSECT-SDK microservices authenticate with a different API-key mechanism.
"""

from ..core.environment import settings
from .definitions import SessionManager

session_manager: SessionManager
if settings.AUTH_IMPLEMENTATION == 'keycloak':
    from .impl_keycloak.get_user import get_user
    from .impl_keycloak.session_manager import session_manager
else:
    from .impl_rudimentary.get_user import get_user
    from .impl_rudimentary.session_manager import session_manager

session_manager.user_loader()(get_user)

__all__ = ['get_user', 'session_manager']
