# pywebview JS API

This directory contains the PyWebView JavaScript client library organized as ES6 modules.

The code is compiled into two bundles in the `webview/js` directory:

- pywebview-api.js - The main bundle containing the core API and functionality
- pywebview-finish.js - A separate bundle to be loaded after `_pywebviewready` Python event is fired. This is done to avoid deadlocks when JS API is initialized..
