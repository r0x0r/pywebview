<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://badge.fury.io/py/pywebview"><img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /></a> <a href="https://travis-ci.org/r0x0r/pywebview"><img src="https://travis-ci.org/r0x0r/pywebview.svg?branch=master" alt="Build Status" /></a> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd?svg=true" alt="Build status" /></a>

https://pywebview.flowrl.com
</p>


_pywebview_ is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. You can use pywebview either with a lightweight web framework like [Flask](http://flask.pocoo.org/) or [Bottle](http://bottlepy.org/docs/dev/index.html) or on its own with a two way bridge between Python and DOM.

_pywebview_ uses native GUI for creating a web component window: WinForms on Windows, Cocoa on macOS and QT or GTK on Linux. If you choose to freeze your application, pywebview does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small. _pywebview_ is compatible with both Python 2 and 3.

_pywebview_ is created by [Roman Sirokov](https://github.com/r0x0r/). Maintained by Roman and [Shiva Prasad](https://github.com/shivaprsdv).


# Getting started

[![Join the chat at https://gitter.im/pywebview/community](https://badges.gitter.im/pywebview/community.svg)](https://gitter.im/pywebview/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

### Install

``` bash
pip install pywebview
```
_On Linux you need additional libraries. Refer to the [installation](https://pywebview.flowrl.com/guide/installation.html) page for details._


### Hello world
```
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
```

Explore _pywebview_ further by reading [documentation](https://pywebview.flowrl.com/guide), [examples](https://pywebview.flowrl.com/examples) or [contributing](https://pywebview.flowrl.com/contributing) .


# Supporting pywebview


_pywebview_ is a BSD licensed open source project. It is an independent project with no corporate backing. If you find _pywebview_ useful, consider supporting it. More donation options are outlined on the [Donating](https://pywebview.flowrl.com/contributing/donating.html) page.

<a href="https://www.patreon.com/bePatron?u=13226105" data-patreon-widget-type="become-patron-button"><img src='https://c5.patreon.com/external/logo/become_a_patron_button.png' alt='Become a Patron!'/></a>


