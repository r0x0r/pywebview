# Development

Before you get busy coding a new feature, create an issue and discuss the details in the issue tracker.

## Environment set-up

This guide assumes you have a [GitHub](https://github.com) account, as well as [Python 3](https://python.org), [virtualenv](https://virtualenv.pypa.io/en/stable/) and [Git](https://git-scm.com) installed. The guide is written for Bash, for Windows you can use for example Bash bundled with Git.

* [Fork](https://github.com/r0x0r/pywebview/fork) _pywebview_
* Clone your forked repository

``` bash
git clone https://github.com/<username>/pywebview
cd pywebview
```

* Create a virtual environment
``` bash
virtualenv -p python3 venv
source venv/bin/activate
pip install -e ".[dev]"
pip install pytest
```

* Set up pre-commit hooks
``` bash
pre-commit install
```

* Hello world
``` bash
python examples/simple_browser.py
```


## Development work-flow

* Create and checkout a new branch
``` bash
git checkout -b new-branch master
```

* Make your changes

* Format and lint your code (this happens automatically with pre-commit)
``` bash
# Manual formatting and linting (optional, pre-commit does this automatically)
ruff check --fix .
ruff format .
```

* Run tests
``` bash
pytest tests
```

* Commit and push your work

``` bash
git add .
git commit -m "Your commit message goes here"  # Pre-commit hooks will run automatically
git push -u origin new-branch
```

* [Create a pull request](https://help.github.com/articles/creating-a-pull-request/)


## Testing

pywebview uses [pytest](https://docs.pytest.org/en/latest/) for testing.

To run all the tests in the project root directory

``` bash
 pytest tests
```

To run a specific test

``` bash
pytest tests/test_simple_browser.py
```

 Tests cover only trivial mistakes, syntax errors, exceptions and such. In other words there is no functional testing. Each test verifies that a pywebview window can be opened and exited without errors when run under different scenarios. Sometimes test fail / stuck randomly. The cause of the issue is not known, any help on resolving random fails is greatly appreciated.

## Code Formatting and Linting

pywebview uses [Ruff](https://docs.astral.sh/ruff/) for code formatting and linting, along with [pre-commit](https://pre-commit.com/) hooks to automatically enforce code quality standards.

### Pre-commit Hooks

Pre-commit hooks are automatically installed when you run `pre-commit install` during setup. They will run automatically before each commit to:

* Fix import sorting
* Apply consistent code formatting (single quotes, line length, etc.)
* Check for large files, trailing whitespace, and YAML syntax
* Run linting checks and apply automatic fixes where possible

### Ruff Configuration

The project uses the following Ruff configuration (defined in `pyproject.toml`):

* **Line length**: 100 characters
* **Quote style**: Single quotes for strings
* **Import sorting**: Enabled with `webview` as a known first-party package
* **Target Python version**: 3.7+
* **Enabled rules**: Pyflakes (F), pycodestyle (E4, E7, E9), isort (I), and pyupgrade (UP)

### Manual Formatting

While pre-commit hooks handle formatting automatically, you can also run formatting manually:

``` bash
# Check for linting issues and apply fixes
ruff check --fix .

# Format code
ruff format .

# Run all pre-commit hooks manually
pre-commit run --all-files
```

### Code Style Guidelines

* Use single quotes for strings (unless the string contains single quotes)
* Maximum line length of 100 characters
* Follow PEP 8 conventions
* Use f-strings instead of `.format()` or `%` formatting where possible
* Remove unused imports and variables
* Use `isinstance()` instead of `type()` comparisons

## Learning

### Windows
* [Windows Forms documentation](https://docs.microsoft.com/en-us/dotnet/framework/winforms/)
* [Windows Forms API](https://docs.microsoft.com/en-us/dotnet/api/system.windows.forms)

### macOS
* [pyobjc](https://pythonhosted.org/pyobjc/). Converting Objective C syntax to Python can be tricky at first. Be sure to check out the [pyobjc intro](https://pythonhosted.org/pyobjc/core/intro.html).
* [AppKit](https://developer.apple.com/documentation/appkit)
* [WebKit](https://developer.apple.com/documentation/webkit)

### Linux
* [PyGObject API reference](https://lazka.github.io/pgi-docs/)

### Qt
* [Qt for Python Documentation](https://doc.qt.io/qtforpython-5/contents.html)
* [Qt5 documentation](https://doc.qt.io/qt-5/index.html)
* [PySide2 QtWidgets](https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/index.html)
