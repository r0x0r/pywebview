from __future__ import annotations

import json

import click

from webview.cli.config import ConfigError
from webview.cli.config import load as load_config


@click.command('config')
@click.option('--path', 'config_path', default=None, type=click.Path(exists=True))
def config(config_path: str | None) -> None:
    """Load and validate pywebview2.conf.json, printing the resolved config."""
    try:
        resolved = load_config(config_path)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e

    click.echo(json.dumps(resolved, indent=2))
