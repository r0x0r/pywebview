from __future__ import annotations

import click

from webview.bundler.doctor import run_all


@click.command()
def doctor() -> None:
    """Check the local environment for pywebview CLI/build prerequisites."""
    results = run_all()
    any_failed = False

    for result in results:
        mark = click.style('OK', fg='green') if result.ok else click.style('MISSING', fg='red')
        click.echo(f'[{mark}] {result.name}: {result.detail}')
        if not result.ok:
            any_failed = True

    if any_failed:
        click.echo(
            '\nSome checks failed. Missing tools only block the build targets that need them.'
        )
