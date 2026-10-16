"""Single owner of the pythonnet bootstrap.

winforms, edgechromium and mshtml all need ``clr``, and all depend on one
easily broken rule: the runtime must be chosen before pythonnet is imported,
since pythonnet reads ``PYTHONNET_RUNTIME`` as it loads. Each backend used to
state that rule itself; it lives here once instead.

The side effect on import is the point. Leaving selection to the caller means
a direct backend import skips it and falls to pythonnet's netfx default,
which does not exist on Windows on ARM64.
"""

from webview.clr_runtime import select_runtime

select_runtime()

# Deliberately after the call above -- pythonnet reads the runtime as it loads.
import clr  # noqa: E402

__all__ = ['clr']
