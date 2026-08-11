"""Choosing the .NET runtime that pythonnet loads on Windows.

coreclr is tried first and netfx is the fallback. pythonnet itself defaults
to netfx, which is no longer a safe default for the WinForms backend: .NET
Framework is absent on Windows on ARM64, and the WebView2 assemblies shipped
for coreclr cannot be loaded by it.

Two details matter for the coreclr attempt:

* It needs a runtimeconfig naming ``Microsoft.WindowsDesktop.App``. Given only
  ``DOTNET_ROOT``, clr_loader synthesizes a base ``Microsoft.NETCore.App``
  config, so the CLR starts without WinForms and ``System.Windows.Forms``
  fails to load.
* That config must not pin a framework major. ``rollForward`` never rolls
  *down*, so a config asking for 10.0 fails outright on a .NET 8 host.

An embedder that has already chosen a runtime -- by setting
``PYTHONNET_RUNTIME``, or by bundling a private .NET with its own
``PYTHONNET_CORECLR_RUNTIME_CONFIG`` -- is never overridden.
"""

from __future__ import annotations

import os
import sys
from typing import Callable

# Assemblies directly in webview/lib target .NETFramework; the .NETCoreApp
# variants live in this subdirectory.
CORECLR_INTEROP_SUBDIR = 'netcoreapp3.0'

RUNTIME_CONFIG = 'pywebview-runtimeconfig.json'


def runtimeconfig_path() -> str:
    """The shipped runtimeconfig naming the WinForms framework."""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', RUNTIME_CONFIG)


def is_coreclr() -> bool:
    """Whether pythonnet is running on coreclr rather than .NET Framework."""
    return os.environ.get('PYTHONNET_RUNTIME') == 'coreclr'


def interop_subdir() -> str:
    """Subdirectory of ``webview/lib`` holding assemblies for the active runtime."""
    return CORECLR_INTEROP_SUBDIR if is_coreclr() else ''


def _load(runtime: str) -> None:
    """Import pythonnet under ``runtime``, which pythonnet reads from the
    environment. select_runtime() has already set it; setting it again
    keeps this usable on its own."""
    os.environ['PYTHONNET_RUNTIME'] = runtime

    try:
        import clr  # noqa: F401
    except BaseException:
        # A failed load leaves partially initialised modules behind, which
        # would poison the fallback attempt.
        for module in ('clr', 'pythonnet'):
            sys.modules.pop(module, None)
        raise


def select_runtime(load: Callable[[str], None] = _load) -> str:
    """Load pythonnet, preferring coreclr. Returns the runtime in use.

    ``PYTHONNET_RUNTIME`` is left naming the runtime that actually loaded, so
    is_coreclr() — and therefore assembly resolution — stays truthful.

    ``load`` is a parameter only so that this selection can be tested where no
    .NET runtime exists; callers should leave it alone.
    """
    chosen = os.environ.get('PYTHONNET_RUNTIME')
    if chosen:
        load(chosen)
        return chosen

    os.environ.setdefault('PYTHONNET_CORECLR_RUNTIME_CONFIG', runtimeconfig_path())

    os.environ['PYTHONNET_RUNTIME'] = 'coreclr'
    try:
        load('coreclr')
    except BaseException:
        os.environ['PYTHONNET_RUNTIME'] = 'netfx'
        load('netfx')
        return 'netfx'

    return 'coreclr'
