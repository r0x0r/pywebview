# Virtual environment

If you create a virtual environment using the built-in Python on macOS, a pywebview window will have issues  with keyboard focus and Cmd+Tab. The issue can be avoided by using other Python installation as described [here](https://virtualenv.pypa.io/en/stable/userguide/#using-virtualenv-without-bin-python). For example to use Python 3 via [Homebrew](https://brew.sh).

``` bash
brew install python3
virtualenv pywebview_env -p python3
```
