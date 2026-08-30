from __future__ import annotations

import os
import platform
import subprocess

import click

from webview.bundler import android, freeze, ios, linux, macos, windows
from webview.cli.config import ConfigError
from webview.cli.config import load as load_config

VALID_TARGETS = {'msi', 'nsis', 'dmg', 'deb', 'appimage', 'android', 'ios'}


def _build_frontend(config: dict, project_dir: str) -> None:
    command = config.get('frontendBuild', {}).get('command')
    if not command:
        return

    click.echo(f'Building frontend: {command}')
    try:
        subprocess.run(command, shell=True, cwd=project_dir, check=True)
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f'Frontend build failed with exit code {e.returncode}') from e

    frontend_dist = os.path.join(project_dir, config['frontendDist'])
    if not os.path.isdir(frontend_dist):
        raise click.ClickException(
            f'Frontend build completed but frontendDist does not exist: {frontend_dist}'
        )


@click.command()
@click.option('--config', 'config_path', default=None, type=click.Path(exists=True))
@click.option('--target', 'targets', multiple=True, help='Override bundle.targets, may repeat')
@click.option('--dist', 'dist_dir', default='dist', show_default=True, help='Output directory')
@click.option('--release', is_flag=True, help='Build an Android release APK instead of debug')
def build(config_path: str | None, targets: tuple[str, ...], dist_dir: str, release: bool) -> None:
    """Freeze the app with PyInstaller and produce native installers."""
    try:
        config = load_config(config_path)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e

    project_dir = os.path.dirname(os.path.abspath(config_path)) if config_path else os.getcwd()
    dist_dir = os.path.abspath(dist_dir)
    requested_targets = list(targets) or config['bundle'].get('targets', [])
    invalid_targets = set(requested_targets) - VALID_TARGETS
    if invalid_targets:
        raise click.ClickException(
            f'Invalid target(s): {", ".join(sorted(invalid_targets))}. '
            f'Valid targets: {", ".join(sorted(VALID_TARGETS))}'
        )

    android_requested = 'android' in requested_targets
    ios_requested = 'ios' in requested_targets
    desktop_targets = [t for t in requested_targets if t not in {'android', 'ios'}]

    built = []
    failures = []
    installers_dir = os.path.join(dist_dir, 'installers')

    if desktop_targets:
        _build_frontend(config, project_dir)

    # Mobile targets are built from source by their native toolchains, not from
    # PyInstaller output -- skip the freeze step when they are the only target.
    if not requested_targets or desktop_targets:
        click.echo(f"Freezing {config['entry']} with PyInstaller...")
        try:
            source_dir = freeze.freeze(config, project_dir, dist_dir)
        except freeze.FreezeError as e:
            raise click.ClickException(str(e)) from e
        click.echo(f'Frozen app at {source_dir}')

    if not requested_targets:
        click.echo('No bundle.targets configured; skipping installer generation.')
        click.echo(
            'Set "bundle.targets" in pywebview2.conf.json or pass --target to build installers.'
        )
        return

    system = platform.system()
    target_map = {
        'msi': ('Windows', lambda: windows.build_msi(config, source_dir, installers_dir)),
        'nsis': ('Windows', lambda: windows.build_nsis_exe(config, source_dir, installers_dir)),
        'dmg': (
            'Darwin',
            lambda: macos.build_dmg(
                config, macos.build_app_bundle(config, source_dir, installers_dir), installers_dir
            ),
        ),
        'deb': ('Linux', lambda: linux.build_deb(config, source_dir, installers_dir)),
        'appimage': ('Linux', lambda: linux.build_appimage(config, source_dir, installers_dir)),
    }

    for target in desktop_targets:
        if target not in target_map:
            failures.append(f'{target}: unsupported target')
            continue

        required_os, build_fn = target_map[target]
        if required_os != system:
            click.echo(f'Skipping {target}: requires {required_os}, running on {system}.')
            failures.append(f'{target}: requires {required_os}, running on {system}')
            continue

        click.echo(f'Building {target}...')
        try:
            artifact = build_fn()
            click.echo(f'  -> {artifact}')
            built.append(artifact)
        except (windows.InstallerError, macos.InstallerError, linux.InstallerError) as e:
            click.echo(f'  ! {target} incomplete: {e}')
            failures.append(f'{target}: {e}')
        except Exception as e:
            click.echo(f'  ! {target} failed: {e}')
            failures.append(f'{target}: {e}')

    if android_requested:
        click.echo('Building android...')
        try:
            apk_path = android.build(config, project_dir, release=release)
            click.echo(f'  -> {apk_path}')
            built.append(apk_path)
        except android.AndroidBuildError as e:
            click.echo(f'  ! android incomplete: {e}')
            failures.append(f'android: {e}')
        except Exception as e:
            click.echo(f'  ! android failed: {e}')
            failures.append(f'android: {e}')

    if ios_requested:
        click.echo('Building ios simulator host...')
        try:
            ios_path = ios.build(config, project_dir, dist_dir)
            click.echo(f'  -> {ios_path}')
            built.append(ios_path)
        except ios.IOSBuildError as e:
            click.echo(f'  ! ios incomplete: {e}')
            failures.append(f'ios: {e}')
        except Exception as e:
            click.echo(f'  ! ios failed: {e}')
            failures.append(f'ios: {e}')

    if built:
        click.echo(f'\nBuilt {len(built)} artifact(s)')
    if failures:
        raise click.ClickException(
            'Build failed:\n' + '\n'.join(f'  - {failure}' for failure in failures)
        )
