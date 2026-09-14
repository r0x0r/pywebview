"""Which runtime actually loaded — the question a green Windows run cannot answer.

``test_clr_runtime.py`` drives ``select_runtime()`` with a fake loader, so it
proves the *decision*: coreclr first, netfx second, an explicit choice honoured.
What it cannot prove is the *outcome* on a real host. ``select_runtime()`` logs
its coreclr→netfx fallback at ``logger.debug`` and then returns normally, so a
Windows run where coreclr was rejected and netfx quietly took over is — to every
other test in this suite — indistinguishable from one where coreclr loaded. Those
two states differ in exactly the thing #1803 is about, which makes the whole
suite green in both and therefore silent about the change under test.

So these tests load pythonnet for real and cross-check our own bookkeeping
against the CLR's report of itself. Windows-only: there is no pythonnet to load
anywhere else.
"""

import os
import platform
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32',
    reason='pythonnet and the .NET runtimes it hosts are Windows-only',
)

# typeof(object).Assembly is the one discriminator that needs no AddReference
# and cannot be spoofed by our own environment: the two runtimes put the core
# library in differently named assemblies, and always have.
CORE_ASSEMBLY = {'coreclr': 'System.Private.CoreLib', 'netfx': 'mscorlib'}


@pytest.fixture(scope='module')
def loaded():
    """``(runtime we claim, name of the CLR's core assembly)``.

    Imported through ``webview.platforms._pythonnet`` rather than by calling
    ``select_runtime()`` directly — that module is the single owner of the
    bootstrap, so this exercises the path every backend actually takes.

    Module-scoped because pythonnet cannot be re-hosted onto a different
    runtime within a process: whatever loads first is what the whole session
    gets. Do not parameterise anything here over runtimes.
    """
    # Import order is load-bearing and the opposite of what isort wants: the
    # ``System`` namespace does not exist until the line above it has loaded
    # pythonnet. Same constraint the backends annotate with E402 at module level.
    from webview.platforms._pythonnet import clr  # noqa: I001
    from System import Object

    core_assembly = clr.GetClrType(Object).Assembly.GetName().Name
    return os.environ['PYTHONNET_RUNTIME'], str(core_assembly)


def test_the_runtime_we_report_is_the_runtime_that_loaded(loaded):
    """The central assertion: our bookkeeping is not lying.

    ``PYTHONNET_RUNTIME`` is not an observation, it is what we wrote. Every
    downstream decision reads it back — ``is_coreclr()`` gates
    ``interop_subdir()``, which chooses which build of the WebView2 assemblies
    to load — so if it disagrees with the CLR that is actually hosting us, the
    backend resolves assemblies for a runtime it is not running on.
    """
    claimed, core_assembly = loaded

    assert claimed in CORE_ASSEMBLY, f'select_runtime() left an unknown runtime: {claimed!r}'
    assert core_assembly == CORE_ASSEMBLY[claimed], (
        f'we report PYTHONNET_RUNTIME={claimed!r}, but the loaded CLR is hosting '
        f'{core_assembly!r} — expected {CORE_ASSEMBLY[claimed]!r}'
    )


def test_coreclr_was_not_silently_rejected(loaded):
    """coreclr is the preferred runtime, so landing on netfx is a finding.

    This is the test that gives the Windows run a voice. Falling back is
    legitimate on a host with no .NET 5+ — the fallback exists precisely for
    that — but it must be *stated*, because it means the coreclr path this
    change is about was never exercised. Reading netfx here is not necessarily
    a bug; reading it without knowing is the problem.
    """
    claimed, _ = loaded

    assert claimed == 'coreclr', (
        'pythonnet came up on .NET Framework, so nothing in this run exercised '
        'the coreclr path. Re-run with PYWEBVIEW_LOG=debug to see why coreclr '
        'was rejected (select_runtime logs the reason at debug level).'
    )


@pytest.mark.skipif(
    platform.machine().lower() not in ('arm64', 'aarch64'),
    reason='only ARM64 lacks .NET Framework outright',
)
def test_arm64_cannot_be_on_netfx(loaded):
    """There is no .NET Framework on Windows on ARM64.

    This is the whole reason the coreclr-first selection exists. If the process
    reports netfx here, either the fallback loaded something that cannot be
    what it claims, or the host is not the ARM64 machine this was meant to run
    on — both worth failing over.
    """
    claimed, core_assembly = loaded

    assert claimed == 'coreclr', f'ARM64 reported {claimed!r}'
    assert core_assembly == 'System.Private.CoreLib'


def test_the_edgechromium_backend_imports(loaded):
    """Importing the backend is itself the assertion.

    ``edgechromium`` resolves its WebView2 assemblies at import time, off
    ``interop_dll_path()`` and therefore off the runtime selected above, and it
    imports the shared WebView2 core from a sibling module. Import is where a
    wrong runtime, a wrong assembly build or a missing name shows up, and it is
    the only cheap check that reaches this file at all — every other test of
    this backend needs a window.
    """
    import webview.platforms.edgechromium as edgechromium

    assert edgechromium.renderer == 'edgechromium'
    assert issubclass(edgechromium.WinFormsEdgeChrome, edgechromium.WebView2Core)


def test_interop_assemblies_match_the_active_runtime(loaded):
    """The WebView2 assemblies that loaded are the ones built for this runtime.

    ``TestFrozenInteropDllPath`` covers the same rule against staged files in a
    tmp dir, which proves the path arithmetic and nothing about what the CLR
    ended up holding. Here the assembly is really loaded, and its ``Location``
    is the CLR's own answer to "which file did you take?"
    """
    # As above: the WebView2 namespace only exists once edgechromium has run its
    # AddReference calls, so this block must not be sorted.
    import webview.platforms.edgechromium  # noqa: F401, I001
    from webview.clr_runtime import CORECLR_INTEROP_SUBDIR, is_coreclr
    from webview.platforms._pythonnet import clr
    from Microsoft.Web.WebView2.Core import CoreWebView2Cookie

    location = str(clr.GetClrType(CoreWebView2Cookie).Assembly.Location)
    in_coreclr_subdir = CORECLR_INTEROP_SUBDIR in location.replace('\\', '/').split('/')

    assert in_coreclr_subdir == is_coreclr(), (
        f'running on {"coreclr" if is_coreclr() else "netfx"} but loaded the WebView2 '
        f'assembly from {location!r}'
    )
