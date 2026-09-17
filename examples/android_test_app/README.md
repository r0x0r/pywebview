# Android pywebview Demo App

An interactive reference application for testing and demonstrating the pywebview API bridge,
state management, and window lifecycle events on Android.

## Features

### Main UI
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

## Usage

### As a Demo App
1. Run `main.py` in pywebview
2. The Window and Device cards populate automatically once the app loads
3. Tap "Refresh" on either card to re-fetch the latest values

### For Testing on Android
There is no buildozer spec in this directory, and the app is not set up to be packaged from
here — `main.py` starts with `ssl=True`, which needs `cryptography`, and that cannot be loaded
by the interpreter python-for-android ships.

The supported, CI-verified way to exercise pywebview on a device is the pytest suite in
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
