from secrets import token_urlsafe

from ..core.environment import settings

_NONCE_ENTROPY = 32


def get_nonce() -> str:
    """
    Before generating an HTML response, you must generate a nonce. This nonce is provided in both the HTML response and the headers.
    """
    return token_urlsafe(_NONCE_ENTROPY)


def _get_html_security_headers(nonce: str) -> dict[str, str]:
    """
    This function should be called when handling any HTML response. It sets the necessary HTML headers (except certificate headers, this should be set by the load balancer / reverse proxy).

    As part of setting these headers, it generates a nonce keyword, which should be passed into the templates as the value of the key "nonce" .

    form-action is only necessary when NOT using HTMX, and the connect-src is only necessary when using HTMX.
    """
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        # form-action is needed for non-Javascript requests, connect-src is needed for HTMX
        'Content-Security-Policy': f"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; connect-src 'self'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; style-src-elem 'nonce-{nonce}'; style-src-attr 'nonce-{nonce}'; img-src 'self'",
    }


# these headers tend to cause issues if you're doing frontend development and reloading the page, so just turn them off
get_html_security_headers = (
    _get_html_security_headers if not settings.DEVELOPMENT_API_KEY else lambda _nonce: {}  # noqa: ARG005
)
