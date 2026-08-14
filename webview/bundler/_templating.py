from __future__ import annotations

import os

import jinja2

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

_env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIR), keep_trailing_newline=True)


def render(template_name: str, **context) -> str:
    return _env.get_template(template_name).render(**context)
