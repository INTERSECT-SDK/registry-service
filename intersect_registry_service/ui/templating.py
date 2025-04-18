"""UI templating definitions"""

from pathlib import Path

from fastapi.templating import Jinja2Templates


def _get_templates() -> Jinja2Templates:
    base_dir = Path(__file__).parent.absolute() / 'templates'
    return Jinja2Templates(
        [
            base_dir / 'layouts',
            base_dir / 'pages',
            base_dir / 'partials',
        ]
    )


TEMPLATES = _get_templates()
