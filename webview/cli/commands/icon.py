from __future__ import annotations

import click

from webview.bundler.icons import generate


@click.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--output', 'output_dir', default='icons', show_default=True, help='Output directory')
def icon(source: str, output_dir: str) -> None:
    """Generate a platform icon set (.ico, .icns, PNGs) from SOURCE image."""
    try:
        generated = generate(source, output_dir)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e

    click.echo(f'Generated {len(generated)} icon file(s) in {output_dir}:')
    for path in generated:
        click.echo(f'  {path}')
