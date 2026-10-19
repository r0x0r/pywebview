import ast
import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from types import SimpleNamespace

import pytest

from webview.util import select_runtime

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
ENV_VARS = (
    'PYTHONNET_RUNTIME',
    'PYTHONNET_CORECLR_RUNTIME_CONFIG',
    'DOTNET_ROOT',
    'DOTNET_ROOT_X64',
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delitem(sys.modules, 'pythonnet', raising=False)
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def loader_that_fails_on(*runtimes):
    """A fake pythonnet loader: records what it was asked to load, and raises for any runtime named here."""
    attempts = []

    def load(runtime):
        attempts.append(runtime)
        if runtime in runtimes:
            raise RuntimeError(f'no {runtime} available')

    load.attempts = attempts
    return load


def loader():
    """A fake pythonnet loader that loads whatever it is asked for."""
    return loader_that_fails_on()


class TestSelectRuntime:
    """The runtime chooser is the core decision; keep only the assertions that matter."""

    def test_prefers_coreclr(self):
        load = loader()
        assert select_runtime(load) == 'coreclr'
        assert load.attempts == ['coreclr']
        assert os.environ['PYTHONNET_RUNTIME'] == 'coreclr'

    def test_falls_back_to_netfx_when_coreclr_is_unavailable(self):
        load = loader_that_fails_on('coreclr')
        assert select_runtime(load) == 'netfx'
        assert load.attempts == ['coreclr', 'netfx']
        assert os.environ['PYTHONNET_RUNTIME'] == 'netfx'

    def test_does_not_fall_back_on_keyboard_interrupt(self):
        attempts = []

        def load(runtime):
            attempts.append(runtime)
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            select_runtime(load)

        assert attempts == ['coreclr']

    def test_explicit_runtime_choice_is_honoured(self, monkeypatch):
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'netfx')
        load = loader()
        assert select_runtime(load) == 'netfx'
        assert load.attempts == ['netfx'], 'must not override an explicit choice'

    @pytest.mark.parametrize('platform,expected', [('win32', 'netfx'), ('darwin', 'mono')])
    def test_default_runtime_uses_platform_default(self, monkeypatch, platform, expected):
        monkeypatch.setattr(sys, 'platform', platform)
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'default')
        load = loader()

        assert select_runtime(load) == expected
        assert load.attempts == [expected]
        assert os.environ['PYTHONNET_RUNTIME'] == expected
        if expected == 'netfx':
            from webview.util import interop_dll_path

            for name in ('Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll'):
                assert Path(interop_dll_path(name)).parent.name == 'net462'

    @pytest.mark.parametrize(
        'kind,expected', [('.NET Framework', 'netfx'), ('CoreCLR', 'coreclr'), ('Mono', 'mono')]
    )
    @pytest.mark.parametrize('requested', [None, 'coreclr', 'netfx'])
    def test_existing_runtime_takes_precedence(self, monkeypatch, kind, expected, requested):
        if requested:
            monkeypatch.setenv('PYTHONNET_RUNTIME', requested)
        monkeypatch.setitem(
            sys.modules,
            'pythonnet',
            SimpleNamespace(get_runtime_info=lambda: SimpleNamespace(kind=kind)),
        )
        load = loader()

        assert select_runtime(load) == expected
        assert load.attempts == [expected]
        assert os.environ['PYTHONNET_RUNTIME'] == expected
        assert 'PYTHONNET_CORECLR_RUNTIME_CONFIG' not in os.environ

        if expected == 'netfx':
            from webview.util import interop_dll_path

            assert (
                Path(interop_dll_path('Microsoft.Web.WebView2.WinForms.dll')).parent.name
                == 'net462'
            )

    def test_imported_pythonnet_without_runtime_still_prefers_coreclr(self, monkeypatch):
        monkeypatch.setitem(
            sys.modules, 'pythonnet', SimpleNamespace(get_runtime_info=lambda: None)
        )
        load = loader()

        assert select_runtime(load) == 'coreclr'
        assert load.attempts == ['coreclr']


class TestRuntimeConfig:
    """The shipped Windows desktop config is the only runtimeconfig contract that matters."""

    def test_coreclr_attempt_points_at_a_windowsdesktop_config(self):
        select_runtime(loader())
        cfg = os.environ['PYTHONNET_CORECLR_RUNTIME_CONFIG']
        assert os.path.isfile(cfg)
        framework = json.load(open(cfg))['runtimeOptions']['framework']
        assert framework['name'] == 'Microsoft.WindowsDesktop.App'
        assert framework['version'] == '6.0.0'
        config = json.loads(Path(cfg).read_text())
        assert config['runtimeOptions']['tfm'] == 'net6.0-windows'
        assert config['runtimeOptions']['rollForward'] == 'LatestMajor'

    def test_an_existing_config_is_left_alone(self, monkeypatch):
        monkeypatch.setenv('PYTHONNET_CORECLR_RUNTIME_CONFIG', '/app/theirs.json')
        select_runtime(loader())
        assert os.environ['PYTHONNET_CORECLR_RUNTIME_CONFIG'] == '/app/theirs.json'

    def test_coreclr_attempt_prefers_x64_dotnet_root_for_x64_python(self, monkeypatch):
        monkeypatch.setattr(sysconfig, 'get_platform', lambda: 'win-amd64')
        monkeypatch.setattr(sys, 'platform', 'win32')
        monkeypatch.setenv('ProgramFiles', r'C:\Program Files')
        x64_root = os.path.join(r'C:\Program Files', 'dotnet', 'x64')
        monkeypatch.setattr(os.path, 'isdir', lambda path: path == x64_root)

        select_runtime(loader())

        assert os.environ['DOTNET_ROOT'] == x64_root
        assert os.environ['DOTNET_ROOT_X64'] == x64_root

    def test_native_arm64_python_does_not_use_the_x64_dotnet_root(self, monkeypatch):
        monkeypatch.setattr(sysconfig, 'get_platform', lambda: 'win-arm64')
        monkeypatch.setattr(sys, 'platform', 'win32')
        monkeypatch.setenv('ProgramFiles', r'C:\Program Files')
        monkeypatch.setattr(os.path, 'isdir', lambda path: path == r'C:\Program Files\dotnet\x64')

        select_runtime(loader())

        assert 'DOTNET_ROOT' not in os.environ
        assert 'DOTNET_ROOT_X64' not in os.environ

    def test_an_existing_dotnet_root_is_left_alone(self, monkeypatch):
        monkeypatch.setattr(sysconfig, 'get_platform', lambda: 'win-amd64')
        monkeypatch.setattr(sys, 'platform', 'win32')
        monkeypatch.setenv('ProgramFiles', r'C:\Program Files')
        monkeypatch.setenv('DOTNET_ROOT', r'D:\custom-dotnet')
        monkeypatch.setenv('DOTNET_ROOT_X64', r'D:\custom-dotnet-x64')
        monkeypatch.setattr(os.path, 'isdir', lambda path: path == r'C:\Program Files\dotnet\x64')

        select_runtime(loader())

        assert os.environ['DOTNET_ROOT'] == r'D:\custom-dotnet'
        assert os.environ['DOTNET_ROOT_X64'] == r'D:\custom-dotnet-x64'


class TestInteropDllPath:
    """WebView2 assemblies must target the selected CLR."""

    def test_netfx_uses_framework_assemblies(self, monkeypatch):
        from webview.util import interop_dll_path

        monkeypatch.setenv('PYTHONNET_RUNTIME', 'netfx')
        for name in ('Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll'):
            path = os.path.join(REPO_ROOT, 'webview', 'lib', 'net462', name)
            assert os.path.isfile(path)
            assert os.path.normpath(interop_dll_path(name)) == os.path.normpath(path)

    def test_coreclr_reuses_flat_lib_assemblies(self, monkeypatch):
        from webview.util import interop_dll_path

        monkeypatch.setenv('PYTHONNET_RUNTIME', 'coreclr')
        lib_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'webview', 'lib')
        )

        for name in ('Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll'):
            flat_path = os.path.normpath(os.path.join(lib_dir, name))
            assert os.path.isfile(flat_path)
            assert os.path.normpath(interop_dll_path(name)) == flat_path


@pytest.mark.parametrize('supports_multiple', [False, True])
@pytest.mark.parametrize('accepted', [False, True])
def test_folder_picker_on_coreclr(supports_multiple, accepted):
    # Extract only this method so the compatibility check can run without Windows or pythonnet.
    path = Path(REPO_ROOT) / 'webview' / 'platforms' / 'winforms.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    dialog_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'OpenFolderDialog'
    )
    method = next(
        node
        for node in dialog_class.body
        if isinstance(node, ast.FunctionDef) and node.name == '_show_folder_browser_dialog'
    )
    method.decorator_list = []
    dialog = SimpleNamespace(SelectedPath='first', ShowDialog=lambda parent: accepted)
    if supports_multiple:
        dialog.Multiselect = False
        dialog.SelectedPaths = ['first', 'second']
    namespace = {
        'WinForms': SimpleNamespace(
            FolderBrowserDialog=lambda: dialog,
            DialogResult=SimpleNamespace(OK=True),
        )
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)

    result = namespace['_show_folder_browser_dialog'](
        None, initialDirectory='initial', allow_multiple=True, title='Folders'
    )

    expected = ('first', 'second') if supports_multiple else ('first',)
    assert result == (expected if accepted else None)
    assert dialog.InitialDirectory == 'initial'
    if supports_multiple:
        assert dialog.Multiselect
    else:
        assert not hasattr(dialog, 'Multiselect')


PROBE = """
import os
import tempfile
from inspect import signature
from types import SimpleNamespace
from unittest.mock import patch
import webview.platforms.edgechromium as edgechromium
import webview.platforms.winforms as winforms
from System import Object
from webview._pythonnet import clr

assert winforms.SystemEvents is not None and winforms.WinForms is not None
assert issubclass(edgechromium.WinFormsEdgeChrome, edgechromium.WebView2Core)
if os.environ['PYTHONNET_RUNTIME'] == 'coreclr':
    open_key = winforms.winreg.OpenKey
    def without_netfx(key, path):
        assert 'NET Framework Setup' not in path, 'coreclr must not require netfx'
        return open_key(key, path)
    with patch.object(winforms.winreg, 'OpenKey', side_effect=without_netfx):
        assert winforms._is_chromium()
signature(edgechromium.WinFormsEdgeChrome.clear_user_data).bind(None, 0)
with tempfile.TemporaryDirectory() as temporary:
    edgechromium._state['private_mode'] = True
    edgechromium._state['storage_path'] = None
    for pid in (0, 2147483647):
        cache = os.path.join(temporary, str(pid))
        os.mkdir(cache)
        # No webview attribute: cleanup must not touch an already disposed control.
        edgechromium.WinFormsEdgeChrome.clear_user_data(SimpleNamespace(user_data_folder=cache), pid)
        assert not os.path.exists(cache)
    edgechromium._state['private_mode'] = False
    cache = os.path.join(temporary, 'persistent')
    os.mkdir(cache)
    edgechromium.WinFormsEdgeChrome.clear_user_data(SimpleNamespace(user_data_folder=cache), 0)
    assert os.path.isdir(cache)
    edgechromium._state['private_mode'] = True
    edgechromium._state['storage_path'] = cache
    edgechromium.WinFormsEdgeChrome.clear_user_data(SimpleNamespace(user_data_folder=cache), 0)
    assert os.path.isdir(cache)
screens = winforms.get_screens()
assert screens and all(screen.width > 0 and screen.height > 0 for screen in screens)
print('PROBE', os.environ['PYTHONNET_RUNTIME'], clr.GetClrType(Object).Assembly.GetName().Name)
"""

CORE_ASSEMBLY = {'coreclr': 'System.Private.CoreLib', 'netfx': 'mscorlib'}


def probe(**env):
    """Import the Windows backends in a fresh interpreter; pythonnet can only be loaded once per process."""
    full_env = {k: v for k, v in os.environ.items() if k not in ENV_VARS}
    full_env.update(env)
    result = subprocess.run(
        [sys.executable, '-c', PROBE],
        cwd=REPO_ROOT,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    line = next(line for line in result.stdout.splitlines() if line.startswith('PROBE'))
    return line.split()[1:]


requires_windows = pytest.mark.skipif(
    sys.platform != 'win32', reason='pythonnet runtimes are Windows-only'
)
requires_netfx = pytest.mark.skipif(
    sys.platform != 'win32' or sysconfig.get_platform() == 'win-arm64',
    reason='.NET Framework is not available to native ARM64 Python',
)


@requires_windows
@pytest.mark.skipif(shutil.which('dotnet') is None, reason='no .NET installation found')
def test_backends_import_on_coreclr():
    assert probe(PYTHONNET_RUNTIME='coreclr') == ['coreclr', CORE_ASSEMBLY['coreclr']]


@requires_netfx
def test_backends_import_on_netfx():
    assert probe(PYTHONNET_RUNTIME='netfx') == ['netfx', CORE_ASSEMBLY['netfx']]


@requires_netfx
def test_unusable_coreclr_falls_back_to_a_working_netfx():
    bogus = os.path.join(REPO_ROOT, 'no-such-dotnet')
    assert probe(DOTNET_ROOT=bogus, DOTNET_ROOT_X64=bogus) == ['netfx', CORE_ASSEMBLY['netfx']]
