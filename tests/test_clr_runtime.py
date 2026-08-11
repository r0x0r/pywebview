import json
import os
import sys

import pytest

from webview.clr_runtime import (
    interop_subdir,
    is_coreclr,
    runtimeconfig_path,
    select_runtime,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ('PYTHONNET_RUNTIME', 'PYTHONNET_CORECLR_RUNTIME_CONFIG'):
        monkeypatch.delenv(var, raising=False)


def loader_that_fails_on(*runtimes):
    """A fake pythonnet loader: records what it was asked to load, and raises
    for any runtime named here."""
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
    """coreclr by default, netfx as fallback (r0x0r on #1803)."""

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

    def test_raises_when_neither_runtime_loads(self):
        load = loader_that_fails_on('coreclr', 'netfx')
        with pytest.raises(RuntimeError):
            select_runtime(load)

    def test_explicit_runtime_choice_is_honoured(self, monkeypatch):
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'netfx')
        load = loader()
        assert select_runtime(load) == 'netfx'
        assert load.attempts == ['netfx'], 'must not override an explicit choice'


class TestRuntimeConfig:
    """The coreclr attempt needs a config naming the WinForms framework.

    DOTNET_ROOT alone makes clr_loader synthesize a base Microsoft.NETCore.App
    config, so the CLR comes up without WinForms and the WebView2 assemblies
    never resolve -- the failure reported on #1803.
    """

    def test_coreclr_attempt_points_at_a_windowsdesktop_config(self):
        select_runtime(loader())
        cfg = os.environ['PYTHONNET_CORECLR_RUNTIME_CONFIG']
        assert os.path.isfile(cfg)
        framework = json.load(open(cfg))['runtimeOptions']['framework']
        assert framework['name'] == 'Microsoft.WindowsDesktop.App'

    def test_the_config_rolls_forward_across_majors(self):
        """rollForward only ever rolls *up*, so anything narrower than
        LatestMajor strands hosts whose runtime is a different major than the
        one named here."""
        options = json.load(open(runtimeconfig_path()))['runtimeOptions']
        assert options['rollForward'] == 'LatestMajor'

    def test_an_existing_config_is_left_alone(self, monkeypatch):
        """Embedders that bundle their own runtime (and config) must win."""
        monkeypatch.setenv('PYTHONNET_CORECLR_RUNTIME_CONFIG', '/app/theirs.json')
        select_runtime(loader())
        assert os.environ['PYTHONNET_CORECLR_RUNTIME_CONFIG'] == '/app/theirs.json'


class TestFrozenInteropDllPath:
    """A frozen app resolves assemblies next to the executable, and must make
    the same per-runtime choice the unfrozen package does -- otherwise a
    bundled coreclr app silently loads the netfx assemblies."""

    @staticmethod
    def stage(tmp_path, name):
        (tmp_path / name).write_bytes(b'netfx')
        (tmp_path / 'netcoreapp3.0').mkdir()
        (tmp_path / 'netcoreapp3.0' / name).write_bytes(b'coreclr')

    def test_frozen_coreclr_uses_the_netcoreapp_copy(self, tmp_path, monkeypatch):
        from webview.util import interop_dll_path

        self.stage(tmp_path, 'NotInThePackage.dll')
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'coreclr')
        monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)

        assert interop_dll_path('NotInThePackage.dll') == str(
            tmp_path / 'netcoreapp3.0' / 'NotInThePackage.dll'
        )

    def test_frozen_netfx_uses_the_flat_copy(self, tmp_path, monkeypatch):
        from webview.util import interop_dll_path

        self.stage(tmp_path, 'NotInThePackage.dll')
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'netfx')
        monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)

        assert interop_dll_path('NotInThePackage.dll') == str(tmp_path / 'NotInThePackage.dll')

    def test_missing_assembly_still_raises(self, monkeypatch):
        from webview.util import interop_dll_path

        monkeypatch.setenv('PYTHONNET_RUNTIME', 'coreclr')
        with pytest.raises(FileNotFoundError):
            interop_dll_path('NoSuchAssembly.dll')


class TestInteropSubdir:
    """WebView2 assemblies are per-target-framework; pick by active runtime."""

    def test_coreclr_uses_the_netcoreapp_assemblies(self, monkeypatch):
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'coreclr')
        assert is_coreclr()
        assert interop_subdir() == 'netcoreapp3.0'

    def test_netfx_uses_the_flat_net462_assemblies(self, monkeypatch):
        monkeypatch.setenv('PYTHONNET_RUNTIME', 'netfx')
        assert not is_coreclr()
        assert interop_subdir() == ''
