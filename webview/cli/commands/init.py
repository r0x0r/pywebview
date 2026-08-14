from __future__ import annotations

import os
import re

import click
import jinja2

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'
)

AVAILABLE_TEMPLATES = ('vanilla', 'vue', 'react')


def _default_identifier(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]+', '', name).lower() or 'app'
    return f'com.example.{slug}'


@click.command()
@click.argument('path', default='.', type=click.Path())
@click.option(
    '--template', 'template_name', default='vanilla', type=click.Choice(AVAILABLE_TEMPLATES)
)
@click.option('--name', 'product_name', default=None, help='Product name for the new app')
@click.option(
    '--identifier', default=None, help='Reverse-DNS bundle identifier, e.g. com.example.app'
)
@click.option('--yes', is_flag=True, help='Skip interactive prompts, use defaults/flags only')
def init(
    path: str, template_name: str, product_name: str | None, identifier: str | None, yes: bool
) -> None:
    """Scaffold a new pywebview project."""
    target_dir = os.path.abspath(path)
    os.makedirs(target_dir, exist_ok=True)

    if os.listdir(target_dir):
        existing_conf = os.path.join(target_dir, 'pywebview.conf.json')
        if os.path.exists(existing_conf):
            raise click.ClickException(f'{existing_conf} already exists, refusing to overwrite.')

    default_name = os.path.basename(target_dir) or 'MyApp'
    if not product_name:
        product_name = default_name if yes else click.prompt('Product name', default=default_name)
    if not identifier:
        default_identifier = _default_identifier(product_name)
        identifier = (
            default_identifier if yes else click.prompt('Identifier', default=default_identifier)
        )

    template_dir = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.isdir(template_dir):
        raise click.ClickException(f'Unknown template: {template_name}')

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir), keep_trailing_newline=True
    )
    context = {'product_name': product_name, 'identifier': identifier}

    for root, _dirs, files in os.walk(template_dir):
        rel_root = os.path.relpath(root, template_dir)
        for filename in files:
            src_rel = os.path.join(rel_root, filename) if rel_root != '.' else filename
            is_jinja = filename.endswith('.jinja')
            dest_name = filename[: -len('.jinja')] if is_jinja else filename
            if dest_name == 'gitignore':
                dest_name = '.gitignore'
            dest_rel = os.path.join(rel_root, dest_name) if rel_root != '.' else dest_name
            dest_path = os.path.join(target_dir, dest_rel)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            if is_jinja:
                template = env.get_template(src_rel.replace(os.sep, '/'))
                content = template.render(**context)
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                with open(os.path.join(root, filename), 'rb') as src_f:
                    data = src_f.read()
                with open(dest_path, 'wb') as dest_f:
                    dest_f.write(data)

    click.echo(f'Created new pywebview project in {target_dir}')
    click.echo('Next steps:')
    if target_dir != os.getcwd():
        click.echo(f'  cd {os.path.relpath(target_dir)}')
    click.echo('  pip install pywebview[cli]')
    if template_name in ('vue', 'react'):
        click.echo('  npm --prefix frontend install')
    click.echo('  pywebview dev')
