"""
pywebview2 CLI entry point: `pywebview2 init | dev | build | icon | doctor | config`
"""

from __future__ import annotations

import click

from webview.cli.commands.build import build
from webview.cli.commands.config_cmd import config
from webview.cli.commands.dev import dev
from webview.cli.commands.doctor import doctor
from webview.cli.commands.icon import icon
from webview.cli.commands.init import init


@click.group()
@click.version_option(package_name='pywebview2')
def main() -> None:
    """pywebview2 project scaffolding, dev server, and installer builder."""


main.add_command(init)
main.add_command(dev)
main.add_command(build)
main.add_command(icon)
main.add_command(doctor)
main.add_command(config)


if __name__ == '__main__':
    main()
