# Android PyWebView Demo App

An interactive reference application for testing and demonstrating the pywebview API bridge,
state management, and window lifecycle events on Android.

## Features

### Main UI
- **API Bridge Tests** — Interactive buttons to test Python function calls (getInteger, getString, etc.)
- **State Synchronization** — Read, write, and reset application state that syncs between Python and JS
- **Window Info** — Display device and window information
- **Results Display** — Color-coded feedback for success and error states

### Developer Tools (⚙️ button)
- **Test Runner Tab** — Run the full Mocha/Chai test suite with visual results
  - Covers all API bridge, state, lifecycle, and cookie tests
  - Auto-runs on app startup
- **Code Evaluator Tab** — Execute Python code directly from JavaScript
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
1. Build with buildozer: `buildozer android debug`
2. Install and run on device or emulator
3. Tests auto-run when the app loads (results in Developer Tools)
4. Use the app's buttons to manually verify features
5. Use Code Evaluator to test custom Python logic

### For Development
- **Interactive Testing** — Use the app buttons to manually verify each feature
- **Live Debugging** — Use Code Evaluator to test Python code changes
- **Automated Tests** — View full Mocha test results in Developer Tools
- **State Inspection** — Monitor state changes in real time

## Notes

This app demonstrates the original Mocha/Chai test suite in a real application context. The pytest
suite (`tests/android/`) provides automated CI testing. This example is ideal for:
- Manual verification of features on actual Android devices
- Interactive debugging of the Python↔JavaScript bridge
- Training and reference for developers learning pywebview
- Ad-hoc testing of custom Python code
