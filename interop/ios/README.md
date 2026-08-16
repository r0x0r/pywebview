# iOS integration

iOS support is built as a native host application which embeds Python and
hosts a `WKWebView`. It is not a PyInstaller or Buildozer target.

## Build boundary

The development environment may generate and validate the project on Linux,
but all iOS compilation must run on a GitHub Actions macOS runner. The
repository should eventually provide:

- a native Swift/Objective-C host;
- an embedded `Python.xcframework` and processed Python standard library;
- a bridge between `WKWebView` messages and the Python JS API;
- a `PyWebViewRuntime` implementation backed by `Python.xcframework`;
- generated Xcode project configuration; and
- simulator validation for pull requests, with signed device builds reserved
  for release workflows.

## Initial supported surface

The first implementation should support one web view and the core pywebview
operations: local/remote URL loading, HTML loading, JavaScript evaluation,
the JavaScript API bridge, navigation/load events, cookies, and application
lifecycle events.

Desktop window operations, system trays, global shortcuts, desktop menus, and
multiple windows are intentionally outside the first iOS milestone.

## CI contract

The iOS workflow must remain split into two paths:

1. unsigned simulator builds and smoke tests for pull requests;
2. signed device/archive/export builds for explicitly requested releases.

No signing credentials should be needed for pull-request validation.

## Runtime boundary

`PyWebViewController` depends on `PyWebViewRuntime`, not directly on Python
headers. The eventual runtime implementation must:

1. initialize Python from the app bundle;
2. configure the bundled standard library and application path;
3. invoke the configured Python entry point;
4. dispatch JavaScript API messages to the existing pywebview bridge; and
5. return JSON-encoded values or errors through the supplied reply callback.

`UnavailablePyWebViewRuntime` exists only to make an incomplete host fail
explicitly during development.

The required embedded interpreter layout and bootstrap sequence are described
in [`PYTHON_RUNTIME.md`](PYTHON_RUNTIME.md).

The Python/native function boundary is specified in
[`NATIVE_MODULE.md`](NATIVE_MODULE.md).

The current simulator builder stages `frontendDist` and the configured Python
entry point into the native host bundle. The host attempts to start
`python/app/main.py`; until the embedded runtime is supplied, it logs an
explicit unavailable-runtime message and continues loading the frontend.

When `Python.xcframework` is present in the staged project, the Xcode build
phase runs `scripts/process_python.sh`, which delegates standard-library and
application processing to the framework's `build_utils.sh`.

The CI builder accepts a prebuilt framework through
`PYWEBVIEW_IOS_PYTHON_XCFRAMEWORK`. Pull-request builds may omit this variable
while the native host is being developed; runtime-enabled builds must provide
a framework containing both device and simulator slices.

The manual `iOS Build` workflow can also build Python-Apple-support on the
macOS runner by enabling its `build_python_runtime` input. The generated
framework is then passed to the normal iOS staging/build path.
