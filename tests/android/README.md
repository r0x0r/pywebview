# Android test suite

Runs pywebview's pytest suite on an Android device or emulator. This is what the
`Android` job in `.github/workflows/ci.yml` builds and runs.

## Layout

- `shared/` — per-file symlinks to the tests in `tests/`. Symlinked per file
  rather than as a directory, since this app lives inside `tests/` and a
  directory symlink would point at its own ancestor.
- `shared/test_cookies_android.py`, `shared/test_request_android.py`,
  `shared/test_window_android.py` — real files, adapted from their desktop
  counterparts. See the comments in each for what differs on Android.
- `webview` — symlink to the package, which is how it gets into the APK.
- `main.py` — entry point. Runs pytest and prints `PYWEBVIEW_TEST_RESULT::`
  markers, which python-for-android's bootstrap forwards to logcat.
- `ci_check.sh` — installs the APK, launches it, watches logcat for the markers.

## Running it

    APP_ANDROID_ARCHS=x86_64 buildozer android debug   # one ABI, as CI does
    ./ci_check.sh                                      # with a device attached

`--arch` cannot be passed through to p4a; buildozer derives its own from the
spec.

## Reading the log

`ci_check.sh` publishes the device log three ways, in increasing order of detail:

- **Live, in the job log**, prefixed `[device]` — pytest's output plus
  `AndroidRuntime`. The only view available while a run is still going.
- **The run's summary page** — pass/fail counts, failed test names and the app's
  output from the start of the session.
- **The `android-logcat-<attempt>` artifact** — the unfiltered log, including
  `chromium`, the WebView internals and JNI aborts.
  `gh run download <run-id> -R r0x0r/pywebview`.

The artifact is in `threadtime` format: date, pid, **tid**, level, tag. The
thread id is what distinguishes the UI thread from the test threads, which is
the distinction both of the problems below turn on.

## Java-facing proxies must never be freed

This is the constraint the app is most likely to trip over. It shows up as:

    JNI DETECTED ERROR IN APPLICATION: use of deleted global reference

pyjnius builds a `PythonJavaClass` proxy by handing Java a **bare pointer** to
the Python object (no incref), and the proxy's jobject is a JNI *global*
reference owned by that same Python object. Collecting it deletes the global
reference and leaves Java holding a dangling pointer, so any proxy Java can
still reach has to live for the whole process.

A single-window app never notices. This suite creates and destroys ~50 windows
in one process, which is what makes per-window frees visible. The lifecycle
callbacks are now registered once and routed to whichever `EventLoop` is
current, the frame callback is gone entirely (see below), and `evaluate_js()`
takes its `ValueCallback` from a pool. Adding a proxy means deciding who owns
it; if it cannot be a process-wide singleton or pooled, park it in
`_retained_proxies`.

This applies to proxies *we* construct. A bare Python function passed where
Java wants a functional interface — the dialog listeners in
`_quit_confirmation()`, say — is not one: pyjnius wraps it in a proxy of its
own and adds that to `activeLambdaJavaProxies`, a module-level set it never
removes from, so those live for the process without our help. The rule is
`PythonJavaClass` instances are ours to keep alive, callables pyjnius converts
are not.

The aborts are nondeterministic — measured between 13% and 86% through the run
on identical code — so **a single green run does not prove much.** Take at least
three samples before believing a change here. The logcat artifact is named per
attempt, so `gh run rerun <id>` is the cheap way.

## Calling the same Java method from two threads at once

The same abort also shows up as

    JNI ERROR (app bug): attempt to use stale Global 0x3d86 (should be 0x3d8a)

— same reference *index*, newer serial, i.e. the slot was freed and handed
straight back out. That one is not about proxy lifetime.

pyjnius binds an instance method by writing the receiver onto the **shared,
class-level** `JavaMethod` descriptor and reading it back in `call_method`,
which caches it and then drops the GIL. Two threads calling the same method at
once therefore race: the second bind can release the first one's receiver while
the call is still in flight.

The backend avoids the race rather than fixing pyjnius:

- `Activity.runOnUiThread` is the only Java method it calls from more than one
  thread, and `base.run_on_ui_thread` holds a lock across the bind and the call.
- `EventLoop.mainloop()` blocks on an `Event` instead of driving a
  `Choreographer` frame callback sixty times a second, which bought nothing and
  amplified the race.

Upcalls from Java threads pywebview does not control (`RequestInterceptor`, the
WebView's own callbacks) still use shared descriptors inside pyjnius. Keeping
upcall volume low is the only lever available from this side.

## Gotchas

- `android.no-byte-compile-python = True` is required. p4a otherwise compiles
  with `-OO` and ships only `.pyc`, which hides the test files from pytest's
  collector *and* strips every `assert`.
- `android` and `pyjnius` must be named in `requirements`. The sdl2 bootstrap
  does not pull them in.
- No `cryptography`, so no `ssl=True`. Its Rust extension cannot load against
  p4a's Python: `cannot locate symbol "_Py_DecRef"`. Cleartext HTTP is granted
  through `manifest_application.xml` instead.
- `pyproject.toml`'s `norecursedirs` keeps the desktop suite out of this
  directory, where the `webview` symlink would otherwise shadow the installed
  package.
