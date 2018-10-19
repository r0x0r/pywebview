# VirtualEnv issues 

Under virtualenv on OS X, a window created with pywebview has issues with keyboard focus and Cmd+Tab. This behaviour is caused by the Python interpreter that comes with virtualenv. To solve this issue, you need to overwrite `your_venv/bin/python` with the Python interpreter found on your system. Alternatively you can configure your virtual environment to use another Python interpreter as described [here](https://virtualenv.pypa.io/en/stable/userguide/#using-virtualenv-without-bin-python).

A virtual environment will not be affected by this issue if Python 3 is installed as a [Framework](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPFrameworks/Concepts/WhatAreFrameworks.html) and the [venv](https://docs.python.org/3/library/venv.html#module-venv) module is used to create the virtual environment. [Homebrew](https://brew.sh) defaults to installing Python 3 as a Framework.
