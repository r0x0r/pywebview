# Contributing to pywebview

Thanks for your interest in _pywebview_. The full contributor documentation lives at
[pywebview.flowrl.com/contributing](https://pywebview.flowrl.com/contributing) and in
[docs/contributing](docs/contributing):

* [Development set-up and work-flow](docs/contributing/development.md)
* [Bug reporting](docs/contributing/bug_reporting.md)
* [Documentation](docs/contributing/documentation.md)
* [Releasing](docs/contributing/release.md)
* [Donating](docs/contributing/donating.md)

## Quick start

```bash
git clone https://github.com/<username>/pywebview
cd pywebview
python3 -m venv venv          # Python 3.10 or newer
source venv/bin/activate
pip install -e ".[dev]"
pre-commit install
python examples/simple_browser.py
```

Before opening a pull request:

```bash
pre-commit run --all-files    # ruff lint + format, whitespace, YAML
pytest tests
```

Add an entry to [docs/CHANGELOG.md](docs/CHANGELOG.md) for any user-visible change, and update
[docs/api](docs/api) when you change the public API.

Before you start work on a new feature, please open an issue to discuss it first.

[AGENTS.md](AGENTS.md) documents the architecture, the backend contract and the coding
conventions in more depth. It is written for AI coding agents, but it is the most complete
description of how the code fits together.
