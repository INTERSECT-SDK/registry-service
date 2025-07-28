"""UI templating definitions"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi.templating import Jinja2Templates
from starlette.templating import pass_context

from ..utils.urls import url_abspath_for

if TYPE_CHECKING:
    from fastapi import Request


@pass_context
def url_abspath_for_tmpl(
    context: dict[str, Any],
    name: str,
    /,
    **path_params: Any,
) -> str:
    request: Request = context['request']
    return url_abspath_for(request, name, **path_params)


def _get_templates() -> Jinja2Templates:
    base_dir = Path(__file__).parent.absolute() / 'templates'
    templates = Jinja2Templates(
        [
            base_dir / 'layouts',
            base_dir / 'pages',
            base_dir / 'partials',
        ]
    )
    templates.env.globals.setdefault('url_abspath_for', url_abspath_for_tmpl)
    return templates


TEMPLATES = _get_templates()
