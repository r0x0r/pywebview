from __future__ import annotations

import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request

import click

from webview.cli._net import pick_free_port, wait_for_url
from webview.cli.config import ConfigError
from webview.cli.config import load as load_config

RELOAD_DEBOUNCE_SECONDS = 0.3
IGNORED_DIR_NAMES = {'dist', 'build', 'node_modules', '__pycache__', '.git', 'installers'}
IGNORED_SUFFIXES = ('.log', '.pyc', '.spec')


def _watch_filter(_change, path: str) -> bool:
    parts = path.replace(os.sep, '/').split('/')
    if any(part in IGNORED_DIR_NAMES for part in parts):
        return False
    if path.endswith(IGNORED_SUFFIXES):
        return False
    return True


def _send_reload_ping(port: int, token: str) -> None:
    req = urllib.request.Request(
        f'http://127.0.0.1:{port}/reload', method='POST', headers={'X-Pywebview-Dev-Token': token}
    )
    try:
        urllib.request.urlopen(req, timeout=2)
    except urllib.error.URLError:
        pass  # app not up yet / already exited, nothing to reload


def _start_app(entry_path: str, project_dir: str, env: dict) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, entry_path], cwd=project_dir, env=env)


def _stop_app(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@click.command()
@click.option('--config', 'config_path', default=None, type=click.Path(exists=True))
@click.option('--no-watch', is_flag=True, help='Run once without watching for file changes')
def dev(config_path: str | None, no_watch: bool) -> None:
    """Run the app for development with debug mode, devtools, and hot reload."""
    try:
        config = load_config(config_path)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e

    project_dir = os.path.dirname(os.path.abspath(config_path)) if config_path else os.getcwd()
    entry_path = os.path.join(project_dir, config['entry'])
    if not os.path.exists(entry_path):
        raise click.ClickException(f'Entry point not found: {entry_path}')

    frontend_dev = config.get('frontendDev', {})
    dev_command = frontend_dev.get('command')
    dev_url = frontend_dev.get('url')
    watch_paths = [
        os.path.join(project_dir, p) for p in frontend_dev.get('watch', [config['frontendDist']])
    ]
    watch_paths = [p for p in watch_paths if os.path.exists(p)]

    frontend_process = None
    if dev_command and dev_url:
        click.echo(f'Starting frontend dev server: {dev_command}')
        frontend_process = subprocess.Popen(dev_command, shell=True, cwd=project_dir)
        click.echo(f'Waiting for {dev_url} to become reachable...')
        if not wait_for_url(dev_url):
            frontend_process.terminate()
            raise click.ClickException(f'Frontend dev server did not become reachable at {dev_url}')

    reload_port = pick_free_port()
    reload_token = secrets.token_hex(16)

    env = os.environ.copy()
    env['PYWEBVIEW_DEV'] = '1'
    env['PYWEBVIEW_DEV_RELOAD_PORT'] = str(reload_port)
    env['PYWEBVIEW_DEV_RELOAD_TOKEN'] = reload_token

    app_process = None
    try:
        click.echo(f'Running {entry_path} (PYWEBVIEW_DEV=1)...')
        app_process = _start_app(entry_path, project_dir, env)

        if no_watch:
            app_process.wait()
            return

        click.echo('Watching for changes (Ctrl+C to stop)...')
        try:
            import watchfiles
        except ImportError as e:
            raise click.ClickException(
                'watchfiles is required for `pywebview dev` file watching. '
                'Install it with `pip install pywebview[cli]`.'
            ) from e

        python_watch_dir = os.path.dirname(entry_path) or project_dir
        watch_targets = (
            list({python_watch_dir, *watch_paths}) if watch_paths else [python_watch_dir]
        )

        try:
            for changes in watchfiles.watch(
                *watch_targets,
                debounce=int(RELOAD_DEBOUNCE_SECONDS * 1000),
                watch_filter=_watch_filter,
            ):
                changed_paths = [path for _change, path in changes]
                py_changed = any(p.endswith('.py') for p in changed_paths)

                if app_process.poll() is not None and not py_changed:
                    # app already exited (e.g. crashed or user closed window); nothing to reload
                    continue

                if py_changed:
                    click.echo('Python file changed, restarting app...')
                    _stop_app(app_process)
                    app_process = _start_app(entry_path, project_dir, env)
                else:
                    click.echo('Frontend file changed, reloading...')
                    _send_reload_ping(reload_port, reload_token)
        except KeyboardInterrupt:
            pass
    finally:
        if app_process is not None:
            _stop_app(app_process)
        if frontend_process is not None:
            frontend_process.terminate()
