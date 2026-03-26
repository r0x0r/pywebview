"""
Test BrowserView.get_instance resilience against freed/None window attributes.

Reproduces a macOS crash where get_instance iterates BrowserView.instances
and compares each instance's .window attribute against a target NSWindow.
When a window has been destroyed (windowWillClose_ releases the window),
a deferred Cocoa callback can fire for another window, causing get_instance
to compare against a freed .window pointer — triggering object_getClass on
invalid memory (EXC_BREAKPOINT/SIGTRAP, pointer authentication trap on ARM64).

The fix makes get_instance:
  1. Use getattr(i, attr, None) with a None check to skip freed attributes
  2. Catch all exceptions (not just AttributeError) during comparison
  3. Continue iterating instead of breaking on error
"""

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'darwin', reason='BrowserView.get_instance is macOS/cocoa only'
)


@pytest.fixture(autouse=True)
def save_restore_instances():
    """Save and restore BrowserView.instances around each test."""
    from webview.platforms.cocoa import BrowserView

    saved = dict(BrowserView.instances)
    BrowserView.instances.clear()
    yield BrowserView
    BrowserView.instances.clear()
    BrowserView.instances.update(saved)


class FakeInstance:
    """Minimal stand-in for a BrowserView instance."""

    def __init__(self, uid, window):
        self.uid = uid
        self.window = window


class CrashyComparison:
    """Simulates a freed Cocoa object: any comparison raises.

    On macOS ARM64, comparing a freed NSWindow pointer triggers
    object_getClass which hits a pointer authentication trap.
    In the real crash this kills the process; here we simulate
    it with a RuntimeError so the test can verify get_instance
    handles it gracefully.
    """

    def __eq__(self, other):
        raise RuntimeError(
            'simulated pointer authentication trap (object_getClass on freed NSWindow)'
        )

    def __hash__(self):
        return id(self)


def test_finds_matching_instance(save_restore_instances):
    BrowserView = save_restore_instances
    sentinel = object()
    BrowserView.instances['a'] = FakeInstance('a', sentinel)
    assert BrowserView.get_instance('window', sentinel) is BrowserView.instances['a']


def test_returns_none_when_no_match(save_restore_instances):
    BrowserView = save_restore_instances
    BrowserView.instances['a'] = FakeInstance('a', object())
    assert BrowserView.get_instance('window', object()) is None


def test_skips_none_window(save_restore_instances):
    """A destroyed window has .window = None after windowWillClose_; must skip it."""
    BrowserView = save_restore_instances
    target = object()
    BrowserView.instances['destroyed'] = FakeInstance('destroyed', None)
    BrowserView.instances['alive'] = FakeInstance('alive', target)
    assert BrowserView.get_instance('window', target) is BrowserView.instances['alive']


def test_all_destroyed_returns_none(save_restore_instances):
    """All windows destroyed — returns None without crashing."""
    BrowserView = save_restore_instances
    BrowserView.instances['d1'] = FakeInstance('d1', None)
    BrowserView.instances['d2'] = FakeInstance('d2', None)
    assert BrowserView.get_instance('window', object()) is None


def test_survives_freed_object_comparison(save_restore_instances):
    """Freed Cocoa objects crash on __eq__; get_instance must skip them.

    Without the fix, this raises RuntimeError (simulating the
    EXC_BREAKPOINT/SIGTRAP that kills the process on ARM64 macOS).
    """
    BrowserView = save_restore_instances
    target = object()
    BrowserView.instances['freed'] = FakeInstance('freed', CrashyComparison())
    BrowserView.instances['alive'] = FakeInstance('alive', target)
    # Should not raise — must skip the freed instance and find the alive one
    result = BrowserView.get_instance('window', target)
    assert result is BrowserView.instances['alive']


def test_missing_attribute_skipped(save_restore_instances):
    """Instance missing the attribute entirely — skipped via getattr default."""
    BrowserView = save_restore_instances
    target = object()
    bare = FakeInstance('bare', None)
    del bare.window
    BrowserView.instances['bare'] = bare
    BrowserView.instances['alive'] = FakeInstance('alive', target)
    assert BrowserView.get_instance('window', target) is BrowserView.instances['alive']
