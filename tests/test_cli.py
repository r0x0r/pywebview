import json

import pytest

from webview.bundler import doctor as doctor_checks
from webview.cli.commands import build as build_command
from webview.cli.config import ConfigError, load


def _write_config(path, **overrides):
    config = {
        'productName': 'Test App',
        'version': '0.1.0',
        'identifier': 'com.example.testapp',
        'entry': 'main.py',
    }
    config.update(overrides)
    path.write_text(json.dumps(config), encoding='utf-8')


def test_config_accepts_frontend_build_command(tmp_path):
    config_path = tmp_path / 'pywebview2.conf.json'
    _write_config(config_path, frontendBuild={'command': 'npm run build'})

    config = load(str(config_path))

    assert config['frontendBuild']['command'] == 'npm run build'


@pytest.mark.parametrize('identifier', ['app', 'example'])
def test_config_requires_reverse_dns_identifier(tmp_path, identifier):
    config_path = tmp_path / 'pywebview2.conf.json'
    _write_config(config_path, identifier=identifier)

    with pytest.raises(ConfigError, match='reverse-DNS'):
        load(str(config_path))


def test_build_frontend_runs_command_and_checks_output(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        (tmp_path / 'frontend' / 'dist').mkdir(parents=True)

    monkeypatch.setattr(build_command.subprocess, 'run', fake_run)
    config = {
        'frontendBuild': {'command': 'npm run build'},
        'frontendDist': 'frontend/dist',
    }

    build_command._build_frontend(config, str(tmp_path))

    assert calls == [('npm run build', {'shell': True, 'cwd': str(tmp_path), 'check': True})]


def test_run_all_only_checks_selected_platform_tools(monkeypatch):
    monkeypatch.setattr(doctor_checks.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(
        doctor_checks, 'check_python', lambda: doctor_checks.CheckResult('python', True, 'ok')
    )
    monkeypatch.setattr(
        doctor_checks,
        'check_pywebview2_backend',
        lambda: doctor_checks.CheckResult('backend', True, 'ok'),
    )
    monkeypatch.setattr(
        doctor_checks,
        'check_pyinstaller',
        lambda: doctor_checks.CheckResult('pyinstaller', True, 'ok'),
    )
    monkeypatch.setattr(
        doctor_checks,
        'check_linux_tools',
        lambda: [doctor_checks.CheckResult('linux', True, 'ok')],
    )
    monkeypatch.setattr(
        doctor_checks,
        'check_android_tools',
        lambda: [doctor_checks.CheckResult('android', False, 'missing')],
    )

    results = doctor_checks.run_all(('deb',))

    assert [result.name for result in results] == ['python', 'backend', 'pyinstaller', 'linux']
