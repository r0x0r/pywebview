# Android Mocha Test Suite

This is the original interactive Mocha/Chai test suite for Android, useful for manual testing
and debugging the pywebview API bridge, state management, and window lifecycle events.

## Features

- **JS API Bridge Tests** — Call Python functions from JavaScript and verify return types
- **State Synchronization Tests** — Verify that `window.pywebview.state` syncs between Python and JS
- **Window Lifecycle Tests** — Test events like `pywebviewready` and window open/close
- **Cookie Management** — Verify cookie handling (client-side and server-side)
- **Python Code Evaluator** — Interactive widget to evaluate Python code live for debugging

## Files

- `main.py` — Python backend with TestAPI and Bottle HTTP server
- `index.html` — Mocha test runner HTML
- `index.js` — Test utilities (state reset, cookie helpers, wait functions)
- `manifest.xml` — Android manifest configuration
- `tests/` — Individual test suites:
  - `test-js-api.js` — API bridge tests
  - `test-state.js` — State synchronization tests
  - `test-events.js` — Window lifecycle event tests
  - `test-window.js` — Window property tests

## Running on Android

1. Build with buildozer: `buildozer android debug`
2. Install and run on device or emulator
3. The test suite auto-runs when the page loads
4. View results in the Mocha test output
5. Use the Python Code Evaluator button to test custom Python code interactively

## Notes

The pytest suite (`tests/android/`) now covers the same functionality automatically. This Mocha
suite is preserved as a reference for interactive testing and debugging scenarios where you want
to manually inspect behavior or try ad-hoc Python code evaluation.
