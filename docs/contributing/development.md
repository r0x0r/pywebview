# Development

Before you get busy coding a new feature, create an issue and discuss the details in the issue tracker.

## Environment set-up

This guide assumes you have a [GitHub](https://github.com) account, as well as [Python 3](https://python.org), [virtualenv](https://virtualenv.pypa.io/en/stable/) and [Git](https://git-scm.com) installed

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
pip intall -e .
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
* Commit and push your work

``` bash
git add .
git commit -m "Your commit message goes here"
git push -u origin new-branch
```

* [Create a pull request](https://help.github.com/articles/creating-a-pull-request/)


## Testing

pywebview uses [pytest](https://docs.pytest.org/en/latest/) for testing. To run tests, simply type `pytest tests` in the project root directory. Tests cover only trivial mistakes, syntax errors, exceptions and such, in other words there is no functional testing. Each test verifies that a pywebview window can be opened and exited without errors when run under different scenarios. Tests are automatically run on a every commit via Travis / AppVeyor pipelines. Note that when run in a CI/CD environment, tests tend to fail randomly. The cause for this issue is not known.

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
* [PyQt5 reference guide](http://pyqt.sourceforge.net/Docs/PyQt5/)
* [Qt5 documentation](https://doc.qt.io/qt-5/index.html)
