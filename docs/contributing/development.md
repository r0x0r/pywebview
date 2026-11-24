# Development

This page explains how to set up _pywebview_ for development and how to submit a change. It applies to people and to coding agents. See [Agentic development](#agentic-development) for the extra rules that apply when an agent writes code.

## Before you start

- **Bug fixes** are always welcome. Open a pull request, or open an issue first if the cause is not clear.
- **New features and public API** need discussion first. Create an issue and wait for the maintainer to approve the idea before you write code. Do not add new settings to `webview.settings`, or new parameters to `webview.start()` or `webview.create_window()`, without that approval. Pull requests that add them without agreement may be declined.
- **Keep changes small.** One pull request should do one thing. Do not mix a fix with reformatting or refactoring.

## Repository layout

```
webview/            the library
  window.py         Window class. Does not import any platform module
  guilib.py         selects the backend
  util.py           JS injection and the JS–Python bridge
  http.py           built-in HTTP server
  js/               Javascript injected into every page
  dom/              Python DOM API
  platforms/        one module per backend
  lib/              bundled binaries. Do not edit
interop/            Java sources for the Android binary in webview/lib
tests/              pytest suite
examples/           one runnable example per feature
docs/               documentation (this site)
```

_pywebview_ has one module per backend in `webview/platforms/`: `winforms.py` (with `edgechromium.py`), `winui3.py`, `cef.py`, `cocoa.py`, `gtk.py`, `qt.py` and `android/`. Every backend implements the same set of module-level functions, and `Window` calls them. If you add a method to `Window`, add it to every backend.

## Environment set-up

You need a [GitHub](https://github.com) account, [Python 3.10 or newer](https://python.org) and [Git](https://git-scm.com). The commands below are for Bash. On Windows you can use the Bash that comes with Git.

1. [Fork](https://github.com/r0x0r/pywebview/fork) the repository and clone your fork.

    ``` bash
    git clone https://github.com/<username>/pywebview
    cd pywebview
    ```

2. Create a virtual environment and install _pywebview_ in editable mode with the development tools.

    ``` bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"
    ```

    Or, if you use [uv](https://docs.astral.sh/uv/):

    ``` bash
    uv sync
    ```

    This creates `.venv` and installs _pywebview_ in editable mode with the development tools. Prefix commands with `uv run` (for example `uv run pytest tests`) or activate the environment with `source .venv/bin/activate`. For the backend extras in the next step, use `uv sync --extra <backend>` instead of `pip install`. Pass the same `--extra` every time you run `uv sync`, because `uv sync` removes packages it was not asked for. Do not use `--all-extras`. Some extras work only on one platform or need system libraries.

3. Install the dependencies of the backend you work on.

    | Platform | Backend | Install |
    | --- | --- | --- |
    | Windows | WinForms + WebView2 | Included. Needs the WebView2 runtime |
    | Windows | WinUI 3 | `pip install -e ".[winui3]"` (Python 3.11 or newer) |
    | Windows | CEF | `pip install -e ".[cef]"` |
    | macOS | Cocoa | Included |
    | Linux | GTK | `pip install -e ".[gtk]"` and the system packages in [Installation](/guide/installation.md) |
    | Linux, macOS | Qt | `pip install -e ".[qt]"` |

4. Install the pre-commit hooks.

    ``` bash
    pre-commit install
    ```

5. Check that it works.

    ``` bash
    python examples/simple_browser.py
    ```

To force a backend, set `PYWEBVIEW_GUI`, for example `PYWEBVIEW_GUI=qt`. Set `PYWEBVIEW_LOG=debug` to see debug logs.

## Development workflow

1. Create a branch from `master`.

    ``` bash
    git checkout -b my-change master
    ```

2. Make your change. Keep it as small as possible. If you fix something in one backend, check the other backends for the same problem.

3. Add or update the supporting files:
    - a test, if the change needs one. See [Testing](#testing)
    - an [example](https://github.com/r0x0r/pywebview/tree/master/examples) if you add a user-facing feature
    - the API reference in `docs/api/README.md` for new or changed API
    - a guide page in `docs/guide/` for new behavior
    - an entry in `docs/CHANGELOG.md`. See [Changelog](#changelog)

4. Format, lint and test.

    ``` bash
    ruff check --fix .
    ruff format .
    pre-commit run --all-files
    pytest tests
    ```

5. Commit and push. See [Commit messages](#commit-messages).

    ``` bash
    git add <files>
    git commit -m "[Core] Fix something"
    git push -u origin my-change
    ```

6. [Create a pull request](https://help.github.com/articles/creating-a-pull-request/) against `master`. Fill in the pull request template.

### Commit messages

Start the subject with the area in brackets, followed by an imperative description: `[Core] Fix window state after minimize`. The area is `Core`, `Cocoa`, `GTK`, `Qt`, `Winforms`, `EdgeChromium`, `CEF`, `Android` or `Docs`. Join several areas with a slash: `[Winforms/EdgeChromium] Fix ...`.

### Changelog

Every change that users can see needs an entry in `docs/CHANGELOG.md`. Add it under the `## Unreleased` heading. If the top of the file is a released version, create that heading. Group entries under **⚡ Features**, **🚀 Improvements** or **🐞 Bug fixes**, and start each entry with the backend in backticks: `All`, `Cocoa`, `GTK`, `QT`, `Winforms`, `EdgeChromium`, `CEF` or `Android`.

``` markdown
- `All` Describe the change from the user's point of view. [#1234](https://github.com/r0x0r/pywebview/issues/1234)
```

## Submitting a pull request

Opening a pull request is the start of the review, not the end. By submitting a pull request, you agree to see it through:

- **Respond to review comments.** Fix what the reviewer asks for, or explain why you disagree. Do not leave comments unanswered.
- **Push fixes as new commits** and say in the thread what you changed. Do not rewrite history while the review is in progress, unless the reviewer asks for it.
- **Keep the pull request working.** If CI fails or `master` changes in a way that conflicts with your branch, fix it.
- **Test what the reviewer cannot.** Say which platforms you tested and which you did not.

Maintainers work on _pywebview_ in their free time, so reviews can take a while. A pull request with no activity for 30 days is marked as stale, and is closed after 5 more days. Any new commit or comment removes the stale mark. You can reopen a closed pull request when you are ready to continue.

## Testing

_pywebview_ uses [pytest](https://docs.pytest.org/en/latest/).

``` bash
pytest tests                          # all tests
pytest tests/test_js_api.py           # one file
PYWEBVIEW_GUI=qt pytest tests         # one backend
```

Run pytest from the repository root or from the `tests` directory. Tests import helpers with relative imports, so they cannot run from an unrelated directory.

Things to know:

- **Tests open real windows.** They are smoke tests, not unit tests. Each test checks that a scenario runs and that the window closes without errors. There is little checking of results beyond `assert_js`.
- **You need a display.** On a headless Linux machine, use Xvfb and set `DISPLAY`. For Qt, you can also set `QT_QPA_PLATFORM=offscreen`.
- **Each test has a 60 second limit** (`pytest-timeout`), so a hung window fails the test instead of blocking the run.

To write a test, create a window, put the test logic in a function that runs in a thread, and pass both to `run_test` from `tests/util.py`.

``` python
import webview

from .util import assert_js, run_test


def test_my_feature():
    window = webview.create_window('Test', html='<script>function f() { return 1 }</script>')
    run_test(webview, window, my_feature)


def my_feature(window):
    assert_js(window, 'f', 1)
```

Keep tests focused. Test the behavior that matters, not every code path. If you add several tests for one change, put them in one test file.

### Smoke test app

`tests/smoke_test` is an app that tests most of _pywebview_ in one run: the JS API, state, window events and functions, cookies, the DOM API, multiple windows and the built-in HTTP server. Run it to check a backend by hand, for example after a change that touches many features.

``` bash
cd tests/smoke_test
python main.py                    # default backend
PYWEBVIEW_GUI=qt python main.py   # one backend
```

The tests start automatically. The **Checks** card turns green if all tests pass, or red with a list of failed tests. The same summary is printed to the terminal. The **Manual checks** card has buttons for the confirmation and file dialogs, which need a person to check them. The app needs network access, because it loads Mocha and Chai from unpkg.com.

The app also runs on Android. Build it with `buildozer android debug deploy run` from the same directory. pytest does not collect the smoke test app, and CI does not run it. See `tests/smoke_test/README.md` for details.

### Continuous integration

Pull requests are checked by GitHub Actions:

| Job | What it does |
| --- | --- |
| Code Quality | Runs `pre-commit run --all-files`, compiles examples and tests, and checks that the Android jar matches `interop/android` |
| Type Check | Runs `mypy webview`. It is advisory: the core modules have existing errors, so a failure is not always yours, but do not add new ones |
| Tests | Runs the test suite on Ubuntu with Qt and GTK, on Windows with EdgeChromium and WinUI 3, and on macOS |

## Code style

Ruff and pre-commit enforce the style. The pre-commit hooks run before each commit and fix what they can.

- Single quotes for strings. Use double quotes only if the string contains a single quote.
- Line length is 100 characters.
- Imports are sorted by Ruff, and `webview` is first-party.
- Enabled lint rules: `E4`, `E7`, `E9`, `F`, `I` and `UP`.
- The minimum Python version is 3.10. Do not use newer syntax or standard library features without a guard.
- Use `logging.getLogger('pywebview')` for logs. Do not use `print()` in library code.
- Write docstrings in the `:param name:` style. Add type hints to new public API, because the package ships `py.typed`.
- Backend modules follow the naming of the native API they wrap, for example `windowDidResize_`. Match the file you edit.

Do not edit generated or bundled files: `webview/_version.py`, `webview/lib/**`, `docs/.vuepress/public/**` and `docs/package-lock.json`. To change the Android binary, edit the source in `interop/android`, rebuild the jar, and say so in the pull request. Do not add dependencies to `pyproject.toml` without asking.

## Agentic development

Coding agents such as Claude Code, Codex, Cursor and Copilot are welcome to help with _pywebview_. The repository has an [`AGENTS.md`](https://github.com/r0x0r/pywebview/blob/master/AGENTS.md) file, which most agents read automatically (`CLAUDE.md` is a link to it). It describes the architecture and the rules in this guide in a form that is written for agents. Make sure your agent reads it before it changes code.

The person who submits the pull request is responsible for it, whoever wrote the code. This means:

- **Read and understand every line** before you submit. Do not submit changes that you cannot explain.
- **Review comments are for you.** You answer them and you make the fixes, with or without the help of an agent. Check the agent's changes the same way as any other change.
- **Check the result yourself.** An agent that runs on your machine can run the tests for the backends installed there. A cloud agent usually cannot, because it has no display and no native web engine. Either way, only some backends can be tested on one machine. Never say that tests pass if they were not run. Say what was verified and on which platform.
- **Keep the scope narrow.** Agents tend to add extra features, abstractions, files and refactoring. Ask for the smallest change that solves the problem and remove anything that was not asked for.
- **Do not let an agent add features or public API** without maintainer approval. This includes settings and parameters. See [Before you start](#before-you-start).
- **Do not let an agent edit generated or bundled files,** or add dependencies.
- **Do not submit bulk or drive-by pull requests.** Fixing a real problem that you understand is useful. Sending many automatically generated changes is not.

Agents can do these tasks well, if you check the result:

- find the same pattern in other backends, which is easy to forget
- write a focused test with `run_test`
- draft the changelog entry and the documentation update
- run `ruff` and `pre-commit` and fix the findings

Platform code is the hardest part for agents. Backends bind to native APIs that an agent cannot run or inspect in a typical sandbox. Prefer changes that are correct by inspection, and test them on the real platform.

## Learning

### Windows

- [Windows Forms documentation](https://docs.microsoft.com/en-us/dotnet/desktop/winforms/)
- [Windows Forms API](https://docs.microsoft.com/en-us/dotnet/api/system.windows.forms)
- [WebView2 documentation](https://learn.microsoft.com/en-us/microsoft-edge/webview2/)
- [pythonnet](https://pythonnet.github.io/)

### macOS

- [PyObjC](https://pyobjc.readthedocs.io/). Converting Objective-C syntax to Python can be tricky at first. Read the PyObjC introduction first.
- [AppKit](https://developer.apple.com/documentation/appkit)
- [WebKit](https://developer.apple.com/documentation/webkit)

### Linux

- [PyGObject API reference](https://lazka.github.io/pgi-docs/)
- [WebKitGTK documentation](https://webkitgtk.org/reference/webkit2gtk/stable/)

### Qt

- [Qt for Python documentation](https://doc.qt.io/qtforpython-6/)
- [QtWebEngine documentation](https://doc.qt.io/qt-6/qtwebengine-index.html)

### Android

- [Android WebView](https://developer.android.com/reference/android/webkit/WebView)
- [Buildozer](https://buildozer.readthedocs.io/en/latest/)
