# Android pywebview Demo App

An interactive reference application for testing and demonstrating the pywebview API bridge,
state management, and window lifecycle events on Android.

## Features

### Main UI
- **API Bridge Tests** — Interactive buttons to test Python function calls (getInteger, getString, etc.)
- **State Synchronization** — Read, write, and reset application state that syncs between Python and JS
- **Window Info** — Display device and window information
- **Results Display** — Color-coded feedback for success and error states
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
  - Provides test methods (getInteger, getString, getDict, etc.)
  - Implements eval() for Python code evaluation
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
2. Click buttons to demonstrate API features
3. Watch state sync in real time
4. Explore window properties

### For Testing on Android
There is no buildozer spec in this directory, and the app is not set up to be packaged from
here — `main.py` starts with `ssl=True`, which needs `cryptography`, and that cannot be loaded
by the interpreter python-for-android ships.

The supported, CI-verified way to exercise pywebview on a device is the pytest suite in
`tests/android/`, which runs the same assertions as every other platform. Use this app as a
desktop reference and for interactive debugging of the bridge.

### For Development
- **Interactive Testing** — Use the app buttons to manually verify each feature
- **Live Debugging** — Use Code Evaluator to test Python code changes
- **Automated Tests** — View full Mocha test results in Developer Tools
- **State Inspection** — Monitor state changes in real time

## Notes

This app demonstrates the original Mocha/Chai test suite in a real application context. The pytest
suite (`tests/android/`) provides automated CI testing on Android. This example is ideal for:
- Interactive debugging of the Python↔JavaScript bridge
- Training and reference for developers learning pywebview
- Ad-hoc testing of custom Python code
