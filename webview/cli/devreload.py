"""
Opt-in loopback control server used by `pywebview dev` for frontend-only
reload: reuses the already-vendored `bottle` dependency rather than adding a
new IPC library. Only ever active when PYWEBVIEW_DEV=1 is set by the `dev`
command, binds to 127.0.0.1 only, and requires a per-run token -- so it can
never activate in a `build`-produced frozen app, and can't be reached from
outside the local machine even during dev.
"""

from __future__ import annotations

import os
import threading
from typing import Any


def maybe_start(window: Any) -> None:
    """
    If PYWEBVIEW_DEV=1 and PYWEBVIEW_DEV_RELOAD_PORT/_TOKEN are set (both are
    set by `pywebview dev`), start a background control server that reloads
    `window`'s page on a POST /reload request carrying the matching token.
    No-op otherwise, so this is safe to call unconditionally from a
    scaffolded main.py.
    """
    if os.environ.get('PYWEBVIEW_DEV') != '1':
        return

    port = os.environ.get('PYWEBVIEW_DEV_RELOAD_PORT')
    token = os.environ.get('PYWEBVIEW_DEV_RELOAD_TOKEN')
    if not port or not token:
        return

    from bottle import Bottle, request, response

    app = Bottle()

    @app.post('/reload')
    def _reload():
        if request.headers.get('X-Pywebview-Dev-Token') != token:
            response.status = 403
            return 'forbidden'
        window.evaluate_js('window.location.reload()')
        return 'ok'

    def _run() -> None:
        app.run(host='127.0.0.1', port=int(port), quiet=True)

    thread = threading.Thread(target=_run, daemon=True, name='pywebview-dev-reload')
    thread.start()
