# Android pytest suite

Runs pywebview's real pytest suite on an Android device or emulator, and is what
the `Android` job in `.github/workflows/ci.yml` builds and runs.

This is separate from `tests/android/`, which is a hand-written Mocha suite
driven by a person looking at a screen. That one stays as it is; this one reuses
the desktop tests instead of reimplementing them in JavaScript.

## Layout

- `shared/` — per-file symlinks to the real tests in `tests/`. Symlinked per
  file rather than as a directory because this app lives *inside* `tests/`, so a
  directory symlink would point at its own ancestor.
- `shared/test_cookies_android.py` — a real file, not a symlink. The desktop
  cookie test asserts on `Domain=127.0.0.1;`, which never matches on Android:
  `get_cookies()` builds the domain from `urlparse().netloc`, port included.
- `webview` — symlink to the package, the same mechanism `tests/android/` uses
  to get it into the APK.
- `main.py` — entry point. Runs pytest and prints `PYWEBVIEW_TEST_RESULT::`
  marker lines, which python-for-android's bootstrap forwards to logcat.
- `ci_check.sh` — installs the APK, launches it, watches logcat for the markers.

## Running it

    buildozer android debug          # add `-- --arch=x86_64` equivalent via APP_ANDROID_ARCHS
    ./ci_check.sh                    # with a device or emulator attached

`APP_ANDROID_ARCHS=x86_64 buildozer android debug` builds one ABI instead of
three, which is what CI does. Note that `--arch` cannot be passed through to
p4a: buildozer derives its own from the spec and appends them.

## Known issue: the suite does not finish

The tests themselves pass — the best complete run was 49 of 52 — but the app
aborts partway through at a nondeterministic point:

    JNI DETECTED ERROR IN APPLICATION: use of deleted global reference

Measured across samples of identical code: 13%, 19%, 67%, 67%, 86%. Because of
that variance, **a single run cannot tell you whether a change helped.** Take at
least three samples before believing anything; `gh run rerun <id> --failed` is
the cheap way, and the logcat artifact is named per attempt so re-runs are
actually distinguishable.

The cause is that the backend frees Java-facing pyjnius proxies while Android
still holds references to them. Freeing a `PythonJavaClass` deletes its JNI
global reference, and touching it afterwards aborts the process. Several
individual instances of this have been fixed — `evaluate_js` freeing the
callback from inside that callback's own upcall, `dismiss()` clearing proxies
before `webview.destroy()`, and `dismiss()` freeing them at all — but it is
systemic rather than a single bug: there is no ownership model tying these
objects' lifetimes to the Java objects that hold them.

A single-window app is unaffected in normal use; this needs ~50 window
create/destroy cycles in one process to show up. The CI job is therefore marked
`continue-on-error` for now: it reports without blocking.

Things that were tried and did *not* fix it, so they need not be retried:
constructing p4a `Runnable`s directly instead of via `@run_on_ui_thread`;
retiring the view's proxies instead of freeing them (helped, did not fix);
additionally retiring the `WebView` and app object (made it worse); retaining
recent `ValueCallback`s in a bounded deque.

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
