# Android test suite

Runs pywebview's real pytest suite on an Android device or emulator, and is what
the `Android` job in `.github/workflows/ci.yml` builds and runs.

It replaces a hand-written Mocha suite that had to be watched on a screen by a
person: reusing the desktop tests means Android is covered by the same
assertions as every other platform, and by whatever is added to them later.

## Layout

- `shared/` — per-file symlinks to the real tests in `tests/`. Symlinked per
  file rather than as a directory because this app lives *inside* `tests/`, so a
  directory symlink would point at its own ancestor.
- `shared/test_cookies_android.py` — a real file, not a symlink. The desktop
  cookie test asserts on `Domain=127.0.0.1;`, which never matches on Android:
  `get_cookies()` builds the domain from `urlparse().netloc`, port included.
- `shared/test_request_android.py` — also a real file. `request_sent` fires on
  Android, but request-header modification and `response_received` both need
  the custom-request path in `PyWebViewClient`, and that is skipped for
  cleartext localhost URLs — which is what the built-in server serves, since
  `ssl=True` is unavailable here (see `buildozer.spec`). So there is no Android
  equivalent of the desktop `test_request_headers` or `test_response.py`.
- `shared/test_window_android.py` — also a real file, covering `get_size()` and
  `get_current_url()`. The desktop URL test navigates to example.org and expects
  `None` for a window with no URL; neither applies here.
- `webview` — symlink to the package, which is how it gets into the APK.
- `main.py` — entry point. Runs pytest and prints `PYWEBVIEW_TEST_RESULT::`
  marker lines, which python-for-android's bootstrap forwards to logcat.
- `ci_check.sh` — installs the APK, launches it, watches logcat for the markers.

## Running it

    buildozer android debug          # add `-- --arch=x86_64` equivalent via APP_ANDROID_ARCHS
    ./ci_check.sh                    # with a device or emulator attached

`APP_ANDROID_ARCHS=x86_64 buildozer android debug` builds one ABI instead of
three, which is what CI does. Note that `--arch` cannot be passed through to
p4a: buildozer derives its own from the spec and appends them.

## Reading the log

The device is the only place anything useful is written, so `ci_check.sh`
publishes it three ways, in increasing order of detail:

- **Live, in the job log.** Everything the app writes is echoed as it happens,
  prefixed `[device]` — pytest's own output, plus `AndroidRuntime` for Java
  crashes. This is the only view available while a run is still going, which is
  what makes a hang diagnosable at all.
- **The run's summary page.** Pass/fail counts, the names of any failed tests
  and the last 400 lines of app output, without opening the log.
- **The `android-logcat-<attempt>` artifact.** The unfiltered device log,
  including the system tags the two views above drop — `chromium`, the
  `WebView` internals and the JNI abort messages. Reach for this when the
  failure is not in the app's own output. `gh run download <run-id> -R
  r0x0r/pywebview`.

The artifact is in `threadtime` format: date, pid, **tid**, level, tag. The
thread id is worth noticing — it is what distinguishes the UI thread from the
test threads, which is the distinction both of the JNI problems below turn on.

## Java-facing proxies must never be freed

This is the constraint the app is most likely to trip over, and it used to abort
the suite at a nondeterministic point with:

    JNI DETECTED ERROR IN APPLICATION: use of deleted global reference

pyjnius builds a `PythonJavaClass` proxy by handing Java a **bare pointer** to
the Python object (`NativeInvocationHandler(<long long><void *>py_obj)` — no
incref), and the proxy's jobject is a JNI *global* reference owned by that same
Python object. Collecting it therefore both deletes the global reference and
leaves Java holding a dangling pointer, so any proxy Java can still reach has to
live for the whole process. pyjnius does this itself for bare callables passed
as functional interfaces — they go into its `activeLambdaJavaProxies` — but
everything the backend constructs is the backend's own problem.

A single-window app never noticed: one window's proxies are created once and
outlive everything. This suite creates and destroys ~50 windows in one process,
which is what made the three per-window frees visible:

| Proxy | Was freed by |
| --- | --- |
| `ActivityLifecycleCallbacks` | `EventLoop.close()` unregistering it, which dropped p4a's only reference |
| `FrameCallback` | being a local in `EventLoop.mainloop()`, dropped when the loop returned |
| `ValueCallback` | eviction from the bounded deque `evaluate_js()` parked callbacks in |

All three now have process lifetime: the lifecycle callbacks are registered once
and routed to whichever `EventLoop` is current, the frame callback is gone
entirely (see below), and `evaluate_js()` takes its `ValueCallback` from a pool
and returns it instead of allocating one per call. `BrowserView.dismiss()`
already retained the view's proxies rather than dropping them.

Adding a proxy means deciding who owns it. If it cannot be a process-wide
singleton or pooled, park it in `_retained_proxies`.

Both aborts were nondeterministic — the first was measured at 13%, 19%, 67%,
67%, 86% and 48% through the run on identical code — so **a single green run
does not prove much.** Take at least three samples before believing a change
here; `gh run rerun <id>` is the cheap way, and the logcat artifact is named per
attempt so re-runs are actually distinguishable.

Things that were tried and did *not* help, so they need not be retried:
constructing p4a `Runnable`s directly instead of via `@run_on_ui_thread`
(which made things worse, because the `__functionstable__` leak was accidentally
keeping proxies alive); retiring the `WebView` and the app object as well.

## Calling the same Java method from two threads at once

Proxy lifetime was only half of it. The same abort also shows up as

    JNI ERROR (app bug): attempt to use stale Global 0x3d86 (should be 0x3d8a)

— same reference *index*, newer serial, i.e. the slot was freed and handed
straight back out. That one is not about proxies at all.

pyjnius binds an instance method by writing the receiver onto the **shared,
class-level** `JavaMethod` descriptor (`self.j_self = jc.j_self` in
`JavaMethod.__get__`, which carries an `XXX FIXME we MUST not change our own
j_self` comment upstream) and reading it back in `call_method`, which caches
`self.j_self.obj` and then drops the GIL to make the call. Two threads calling
the same method at the same time therefore race: the second `__get__` can
release the first one's receiver — deleting its global reference — while the
first is still in flight.

The backend cannot fix pyjnius, so it avoids the race instead:

- `Activity.runOnUiThread` is the only Java method this backend calls from more
  than one thread, and `base.run_on_ui_thread` now holds a lock across the bind
  and the call. It is also the backend's own decorator rather than p4a's, which
  additionally fixes p4a caching one never-released `Runnable` per decorated
  function and storing call arguments on that shared proxy.
- `EventLoop.mainloop()` used to drive a `Choreographer` frame callback and now
  simply blocks on an `Event`. Nothing ran per frame, so all the loop
  contributed was sixty Java calls and sixty Python upcalls a second running
  concurrently with everything else — the perfect amplifier for the race above.
  `Choreographer` and `FrameCallback` are gone with it.

Upcalls from Java threads pywebview does not control (`RequestInterceptor`, the
WebView's own callbacks) still use shared descriptors inside pyjnius. Keeping
upcall volume low is the only lever available from this side.

## Gotchas worth knowing

- `android.no-byte-compile-python = True` is required. p4a otherwise compiles
  the app with `-OO` and ships only `.pyc`, which hides the test files from
  pytest's collector *and* strips every `assert`, so the suite would pass
  vacuously.
- `android` and `pyjnius` must be named in `requirements`. The sdl2 bootstrap
  does not pull them in, and without them `import webview.platforms.android`
  fails with `ModuleNotFoundError`.
- No `cryptography`, so no `ssl=True`. It builds, but its Rust extension cannot
  load: `cannot locate symbol "_Py_DecRef"` against p4a's Python 3.14. Cleartext
  HTTP is granted through `manifest_application.xml` instead.
- `pyproject.toml`'s `norecursedirs` keeps the desktop suite out of this
  directory. Without it pytest collects the symlinked tests a second time and,
  worse, puts this directory on `sys.path`, where the `webview` symlink shadows
  the installed package for the whole session.
