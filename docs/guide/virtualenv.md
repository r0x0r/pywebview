# Virtual environment

If you create a virtual environment using the built-in Python on macOS, a pywebview window will have issues  with keyboard focus and Cmd+Tab. The issue can be avoided by using other Python installation as described [here](https://virtualenv.pypa.io/en/stable/userguide/#using-virtualenv-without-bin-python). For example, Python 3 installed via Homebrew](https://brew.sh) does not 

``` bash
brew install python3
virtualenv pywebview_env -p python3
```
