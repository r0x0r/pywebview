<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://badge.fury.io/py/pywebview"><img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /></a> <a href="https://travis-ci.org/r0x0r/pywebview"><img src="https://travis-ci.org/r0x0r/pywebview.svg?branch=master" alt="Build Status" /></a> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd?svg=true" alt="Build status" /></a>

https://pywebview.flowrl.com
</p>


pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. You can use pywebview either with a lightweight web framework like [Flask](http://flask.pocoo.org/) or [Bottle](http://bottlepy.org/docs/dev/index.html) or on its own with a two way bridge between Python and DOM.

pywebview uses native GUI for creating a web component window: WinForms on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you choose to freeze your application, pywebview does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small. Compatible with both Python 2 and 3. While Android is not supported, you can use the same codebase with solutions like [Python for Android](https://github.com/kivy/python-for-android) for creating an APK.

Licensed under the BSD license. Maintained by [Roman Sirokov](https://github.com/r0x0r/) and [Shiva Prasad](https://github.com/shivaprsdv).


# Getting started

Install

``` bash
pip install pywebview
```

Hello world
```
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
```

Explore _pywebview_ further by reading [documentation](https://pywebview.flowrl.com/guide), [examples](https://pywebview.flowrl.com/examples) or [contributing](https://pywebview.flowrl.com/contributing) .


# Supporting pywebview

pywebview is a BSD licensed open source project. It is an independent project with no corporate backing. If you find it useful, consider supporting it.

<a href="https://www.patreon.com/bePatron?u=13226105" data-patreon-widget-type="become-patron-button"><img src='https://c5.patreon.com/external/logo/become_a_patron_button.png' alt='Become a Patron!'/></a>


