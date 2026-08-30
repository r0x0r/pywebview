from __future__ import annotations

import click

from webview.bundler.doctor import run_all

VALID_TARGETS = {'msi', 'nsis', 'dmg', 'deb', 'appimage', 'android', 'ios'}


@click.command()
@click.option('--target', 'targets', multiple=True, help='Check prerequisites for this target')
def doctor(targets: tuple[str, ...]) -> None:
    """Check the local environment for pywebview2 CLI/build prerequisites."""
    invalid_targets = set(targets) - VALID_TARGETS
    if invalid_targets:
        raise click.ClickException(f'Unknown target(s): {", ".join(sorted(invalid_targets))}')
    results = run_all(targets or None)
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
        if targets:
            raise click.exceptions.Exit(1)
