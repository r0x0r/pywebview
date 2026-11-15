# pywebview Smoke Test App

A smoke test application that exercises as much of pywebview as possible in one run and shows
at a glance whether anything is broken. It runs on desktop (Cocoa, GTK, Qt, WinForms, WinUI 3,
CEF) and on Android.

```bash
cd tests/smoke_test
python main.py                  # default backend
PYWEBVIEW_GUI=qt python main.py # force a backend
```

The test suite runs automatically. The **Checks** card turns green when everything passes or red
with the failing checks listed. The same summary is printed to the terminal. Tests that cannot
work on Android (window manipulation, multiple windows) are skipped there. The suite needs network
access, since Mocha and Chai are loaded from unpkg.com.

What is covered:
- Built-in HTTP server with a Bottle WSGI app, static files and a server-set cookie
- JS API: nested API objects, return types, exceptions, async functions, `window.expose`
- `evaluate_js` (return types, promises with a callback, `JavascriptException`), `run_js`,
  `load_css`
- State synchronisation in both directions
- Window events: `before_load`, `loaded`, `before_show`, `shown`, `request_sent`,
  `response_received`, `resized`, `moved`, `minimized`, `maximized`, `restored`, `closed`
- Window functions: title, resize, move, minimize, maximize, restore, fullscreen, on top,
  hide/show, current URL, screens, token
- Cookies: `get_cookies` and `clear_cookies`
- DOM API: creating, querying, traversing and manipulating elements, DOM events
- Multiple windows: create, evaluate, `load_html`, `destroy`
- App menu (desktop) with a *Re-run tests* action
- Manual checks for confirmation and file dialogs, which need a human

## Features

### Main UI
- **Checks** — Summary banner plus pass/fail/skip counts per suite, with failure messages
- **Manual checks** — Buttons that open the confirmation and file dialogs
- **Window info** — Live window title, size, position, fullscreen/on-top flags and screen count,
  fetched from Python via `get_window_info()`
- **Device info** — Live browser/device details from the WebView (user agent, screen resolution,
  pixel ratio, orientation, connectivity, timezone)
- **Status pill** — Shows live pass/fail test counts; tap it to open full test details

### Developer Tools (status pill / tests tab)
- **Tests Tab** — Full Mocha/Chai test suite results
  - Covers all API bridge, state, lifecycle, and cookie tests
  - Runs automatically as soon as the app loads — no manual trigger needed
  - "Re-run all tests" reloads the app to start a fresh test run
- **Console Tab** — Execute Python code directly from JavaScript
  - Use Ctrl+Enter to run code quickly
  - Test arbitrary Python expressions

## Architecture

### Files
- `main.py` — Python backend with TestAPI and Bottle HTTP server
  - Provides test methods (getInteger, getString, getDict, etc.) used by the test suite
  - `WindowAPI` (`api.win`) and `DomAPI` (`api.dom`) drive window functions and the DOM API
    from Python, waiting for the matching window events
  - Implements `get_window_info()` for the Window info card
  - Implements `eval()` for Python code evaluation
  - Sets up window state and event handlers
- `index.html` — Modern app UI with developer tools modal
- `index.js` — Test utilities (state reset, cookie helpers, wait functions)
- `manifest.xml` — Android manifest configuration
- `tests/` — Mocha test suites
  - `test-js-api.js` — API bridge tests
  - `test-state.js` — State synchronization tests
  - `test-events.js` — Window lifecycle event tests
  - `test-window.js` — Window property tests
  - `test-window-functions.js` — Window functions, multiple windows (desktop only)
  - `test-dom.js` — Python DOM API tests

## Usage

### As a Demo App
1. Run `main.py` in pywebview
2. The Window and Device cards populate automatically once the app loads
3. Tap "Refresh" on either card to re-fetch the latest values

### For Testing on Android
The app can be packaged with the `buildozer.spec` in this directory. The supported,
CI-verified way to exercise pywebview on a device is the pytest suite in
`tests/android/`, which runs the same assertions as every other platform. Use this app as a
desktop reference and for interactive debugging of the bridge.

### For Development
- **Live Debugging** — Use Code Evaluator to test Python code changes
- **Automated Tests** — View full Mocha test results in Developer Tools
- **Window/Device Inspection** — Monitor window and device info in real time

## Notes

This app demonstrates the original Mocha/Chai test suite in a real application context. The pytest
suite (`tests/android/`) provides automated CI testing on Android. This example is ideal for:
- Interactive debugging of the Python↔JavaScript bridge
- Training and reference for developers learning pywebview
- Ad-hoc testing of custom Python code
