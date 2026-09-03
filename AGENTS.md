# AGENTS.md

Guidance for AI coding agents working in the _pywebview_ repository. Human contributors should
start with [docs/contributing/development.md](docs/contributing/development.md) — this file
complements it with the conventions and pitfalls that are easy to miss.

## What this project is

_pywebview_ is a lightweight cross-platform wrapper around the native webview component of the
host OS. Python code creates windows; content is HTML/CSS/JS rendered by the system web engine.
The library ships no GUI toolkit and no browser of its own — it binds to what the platform
already has.

Supported platforms and their renderers:

| Platform | Module | Renderer |
| --- | --- | --- |
| Windows | `webview/platforms/winforms.py` | WinForms host for `edgechromium.py` (WebView2) or `mshtml.py` (legacy IE) |
| Windows | `webview/platforms/cef.py` | CEF (opt-in, `cefpython3`) |
| macOS | `webview/platforms/cocoa.py` | Cocoa + WKWebView via PyObjC |
| Linux/BSD | `webview/platforms/gtk.py` | GTK 3 + WebKit2 via PyGObject |
| Linux/BSD/any | `webview/platforms/qt.py` | Qt5/Qt6 + QtWebEngine via QtPy |
| Android | `webview/platforms/android/` | Android WebView via pyjnius |

## Repository layout

```
webview/              the library
  __init__.py         public API: start(), create_window(), settings, module state
  window.py           Window class — the user-facing object, delegates to the active backend
  guilib.py           backend detection and import
  util.py             JS injection, the JS↔Python bridge dispatcher, path helpers, _TOKEN
  http.py             built-in Bottle HTTP server (per-window and global)
  event.py            Event / EventContainer
  state.py            window.state — dict synced with window.pywebview.state in JS
  dom/                Python-side DOM API (Element, DOM, classlist, propsdict)
  js/                 JS injected into every page: api.js, customize.js, state.js, finish.js, lib/
  platforms/          one module per backend (see table above)
  lib/                bundled binaries (WebView2 DLLs, Android jar) — do not edit by hand
  __pyinstaller/      PyInstaller hook
interop/              C# (mshtml) and Java (Android) sources for the binaries in webview/lib
tests/                pytest suite — each test opens a real window
examples/             runnable single-file examples, one feature each
docs/                 VuePress site (guide, api, contributing, CHANGELOG)
```

## Architecture rules

**`Window` is backend-agnostic.** `webview/window.py` never imports a platform module. It holds
state and calls `self.gui.<function>(..., self.uid)`, where `self.gui` is the module chosen by
`guilib.initialize()`. Anything platform-specific belongs in `webview/platforms/`.

**Every backend implements the same module-level function contract.** The canonical list is the
set of module-level functions in `webview/platforms/cocoa.py`: `setup_app`, `create_window`,
`get_active_window`, `set_title`, `create_confirmation_dialog`, `create_file_dialog`, `load_url`,
`load_html`, `destroy_window`, `hide`, `show`, `toggle_fullscreen`, `set_on_top`, `resize`,
`maximize`, `minimize`, `restore`, `move`, `get_current_url`, `clear_cookies`, `get_cookies`,
`evaluate_js`, `get_position`, `get_size`, `get_screens`, `add_tls_cert`, plus a module-level
`renderer` string. **Adding a method to `Window` means adding it to every backend** — including
`cef.py`, `mshtml.py` and `android/`, which are easy to forget. If a backend genuinely cannot
support a feature, log a warning and return a sane default rather than raising.

**Windows are addressed by `uid`.** Backends keep their own registry of native windows keyed by
`window.uid`; the Python `Window` object never holds a native handle except `window.native`,
which the backend assigns after creation.

**API calls are gated on lifecycle events.** `Window` methods are decorated with `@_shown_call`,
`@_loaded_call`, `@_before_load_call` or `@_pywebview_ready_call` (see `window.py`). These block
until the corresponding `Event` fires and raise `WebViewException` on timeout. Use the existing
decorators instead of writing ad-hoc readiness checks, and pick the earliest event that is
actually required.

**`webview.start()` must run on the main thread** and blocks until the last window closes. User
code runs in `func` (a background thread) or in event handlers. Backend code that touches native
UI must be marshalled onto the GUI thread using that backend's mechanism
(`PyObjCTools.AppHelper.callAfter`, `GLib.idle_add`, `Invoke`, Qt signals, …).

**The JS bridge.** `util.inject_pywebview()` builds the injected script from `webview/js/*.js` in
a fixed order (polyfill → api → the rest → `finish.js`, which must be evaluated last and
separately). `%(name)s` placeholders in those files are filled by `load_js_files()`; if you add a
placeholder to a JS file you must add the matching key there or every page load breaks with a
`KeyError`. Calls from JS arrive at `util.js_bridge_call()`, which also handles the internal
`pywebviewDomEvent`, `pywebviewAsyncCallback`, `pywebviewStateUpdate` and `pywebviewStateDelete`
function names.

**`webview.token` / `_TOKEN`** is a session-unique token generated in `util.py` and made
available to both domains — `webview.token` in Python, `window.pywebview.token` in JS — so that
applications can protect their own REST API against CSRF (see `docs/guide/security.md` and
`examples/flask_app`). It is deliberately injected into the page, but it must stay per-session
and unguessable: never persist it, never derive it from anything predictable.

**Settings vs. state.** `webview.settings` is a user-facing `ImmutableDict` of tunables read at
runtime; `webview._state` is internal process state set by `start()`. Read settings at the point
of use, not at import time — a value captured at import cannot be overridden by user code.

## Code style

Enforced by Ruff + pre-commit (`pyproject.toml`, `.pre-commit-config.yaml`); the CI `Code Quality`
job runs `pre-commit run --all-files`.

- **Single quotes** for strings; double quotes only when the string contains a single quote.
- **Line length 100**, 4-space indent, `insert_final_newline`, no trailing whitespace.
- Import sorting via Ruff isort, `webview` is first-party.
- Enabled lint rules: `E4`, `E7`, `E9`, `F`, `I`, `UP`. Markdown is excluded — Ruff formats
  Python blocks inside `.md`, and the documentation samples are written for readability.
- **Target Python is 3.10** (`requires-python = ">=3.10"`). PEP 585 built-in generics
  (`list[str]`), PEP 604 unions (`str | None`) and `match` are all fine at runtime, with or
  without `from __future__ import annotations`. Anything newer must be guarded: `Self` and
  `Unpack` come from `typing_extensions` (3.11), and `state.py` keeps a `try/except ImportError`
  shim for `StrEnum` (3.11).
- Module logger is always `logging.getLogger('pywebview')`. Use `logger.debug` for tracing,
  `logger.exception` inside `except` blocks. Do not `print()` in library code.
- Docstrings use the `:param x:` reST style seen in `window.py` and `__init__.py`. Public API
  functions and `Window` methods should have one; internal helpers usually get a short summary.
- Type hints on new public API. The package ships `py.typed`, so annotations are part of the
  contract.
- Backend modules are the exception to strictness — they mirror the native API's naming
  (`windowDidResize_`, `OnNavigationCompleted`). Match the surrounding file, not PEP 8.

Run before committing:

```bash
ruff check --fix .
ruff format .
pre-commit run --all-files
```

CI also runs `mypy webview` as an **advisory** job (`continue-on-error`). The core modules carry
a backlog of ~118 annotation errors, so a red type-check job is not necessarily your fault —
but do not add to it. Platform backends are excluded from mypy in `[tool.mypy]`, since they bind
to native APIs it cannot introspect.

## Tests

```bash
pytest tests                     # everything
pytest tests/test_js_api.py      # one file
PYWEBVIEW_GUI=qt pytest tests    # force a backend
```

- Tests open **real windows**. They are integration smoke tests, not unit tests: each verifies
  that a scenario runs and the window exits cleanly. There is little functional assertion beyond
  what `assert_js` checks.
- Write tests using `tests/util.py`: create the window, put the test logic in a `thread_func`,
  and hand both to `run_test(webview, window, thread_func)`. `assert_js(window, 'func', expected)`
  round-trips a call through the JS bridge.
- `tests/conftest.py` reloads `webview` and `webview.http` between tests and sets
  `PYWEBVIEW_TEST=true`. Module-level state in the library must survive that reload.
- Tests import helpers relatively (`from .util import run_test`), so run pytest from the repo
  root or from `tests/` — not against a single file path from an unrelated directory.
  `[tool.pytest.ini_options]` sets `testpaths = ["tests"]` and a 60s per-test `timeout`
  (`pytest-timeout`, part of the `dev` extra), so a hung window fails the test instead of
  blocking the run.
- **Some tests fail or hang intermittently**, especially on Windows. A single failure is not
  proof of a regression; re-run before concluding, and say so plainly if you cannot tell.
- Agents in a headless environment usually **cannot run the suite at all** (no display, no
  WebView2, no PyObjC). Do not claim tests pass when you have not run them — state what you
  verified and what you could not.

Useful environment variables: `PYWEBVIEW_GUI` (force a backend), `PYWEBVIEW_LOG` (`debug`,
`error`, …), `PYWEBVIEW_TEST`, `QT_QPA_PLATFORM=offscreen`, `DISPLAY` for Xvfb.

## Examples

`examples/` holds single-file, runnable demonstrations of one feature each, named after the
feature (`drag_drop.py`, `state.py`). A new user-facing feature should come with an example. Keep
them minimal, guard the entry point with `if __name__ == '__main__':`, and inline the HTML as a
module-level string unless assets are the point of the example.

## Documentation

Documentation lives in `docs/` and is published from the `docs` branch (merged from `master` on
release by `.github/workflows/docs.yaml`).

- New or changed API → update `docs/api/README.md`.
- New behaviour or concept → `docs/guide/`.
- Every user-visible change → an entry in `docs/CHANGELOG.md` under the `## Unreleased`
  heading (create it if the top of the file is a released version),
  in the established format: `` - `Backend` Description. Thanks @user. [#1234](link) `` grouped
  under **⚡ Features**, **🚀 Improvements** or **🐞 Bug fixes**. `Backend` is `All`, `Cocoa`,
  `GTK`, `QT`, `Winforms`, `EdgeChromium`, `CEF`, `MSHTML` or `Android`.
- User-facing strings must go through `webview/localization.py`, not be hardcoded in a backend.

## Commits and pull requests

- Commit subject format used in this repo: `[Scope] Imperative description`, where scope is the
  backend or area — `[Core]`, `[Cocoa]`, `[GTK]`, `[Qt]`, `[Winforms]`, `[EdgeChromium]`,
  `[CEF]`, `[MSHTML]`, `[Android]`, `[Docs]`. Multiple scopes are slash-separated:
  `[Winforms/EdgeChromium/MSHTML] Fix ...`.
- One logical change per commit. Do not mix a fix with reformatting.
- Branch off `master` and open the PR against `master`.
- The version number is derived from git tags by `setuptools_scm` and written to
  `webview/_version.py`. Never edit that file or hardcode a version.

## Working agreements for agents

- **Never edit generated or vendored files**: `webview/_version.py`, `webview/lib/**` (DLLs, jar,
  runtimes), `docs/.vuepress/public/**` (archived doc snapshots), `docs/package-lock.json`.
  Binaries in `webview/lib` are built from `interop/` — change the source there and note that the
  binary needs rebuilding.
- **Do not add dependencies** to `pyproject.toml` without asking. The small dependency footprint
  (`bottle`, `proxy_tools`, `typing_extensions` plus per-platform bindings) is a deliberate
  design goal.
- **A change to one backend is usually a change to all of them.** Before declaring a fix
  complete, grep the other platform modules for the same pattern and say explicitly which
  backends you changed and which you could not test.
- **You cannot test most backends.** macOS/Windows/Linux/Android behaviour cannot be verified
  from a single machine. Prefer changes that are obviously correct by inspection, keep them
  narrow, and flag anything that needs verification on hardware you do not have.
- **Preserve backwards compatibility.** Deprecations follow the `@module_property` +
  `logger.warning` pattern in `__init__.py` — warn for a release cycle rather than removing.
- Match the file you are editing. This codebase is old and its styles are not uniform; local
  consistency beats global consistency.
