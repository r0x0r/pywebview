<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://opencollective.com/pywebview" alt="Financial Contributors on Open Collective"><img src="https://opencollective.com/pywebview/all/badge.svg?label=financial+contributors" /></a> <img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /> <img src="https://img.shields.io/pypi/dm/pywebview" alt="PyPI downloads" /> <a href="https://travis-ci.org/r0x0r/pywebview"><img src="https://travis-ci.org/r0x0r/pywebview.svg?branch=master" alt="Build Status" /></a> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd/branch/master?svg=true" alt="Build status" /></a>

https://pywebview.flowrl.com
</p>


_pywebview_ is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. You can use pywebview either with a lightweight web framework like [Flask](http://flask.pocoo.org/) or [Bottle](http://bottlepy.org/docs/dev/index.html) or on its own with a two way bridge between Python and DOM.

_pywebview_ uses native GUI for creating a web component window: WinForms on Windows, Cocoa on macOS and QT or GTK on Linux. If you choose to freeze your application, pywebview does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small. _pywebview_ is compatible with Python 3.

_pywebview_ is created by [Roman Sirokov](https://github.com/r0x0r/).


# Getting started

### Install

``` bash
pip install pywebview
```
_On Linux you need additional libraries. Refer to the [installation](https://pywebview.flowrl.com/guide/installation.html) page for details._


### Hello world
``` python
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
webview.start()
```

Explore _pywebview_ further by reading [documentation](https://pywebview.flowrl.com/guide), [examples](https://pywebview.flowrl.com/examples) or [contributing](https://pywebview.flowrl.com/contributing). If React is your thing, get started right away with [React boilerplate](https://github.com/r0x0r/pywebview-react-boilerplate).



# Contributors

### Code Contributors

This project exists thanks to all the people who contribute. [[Contribute](CONTRIBUTING.md)].
<a href="https://github.com/r0x0r/pywebview/graphs/contributors"><img src="https://opencollective.com/pywebview/contributors.svg?width=890&button=false" /></a>

### Financial Contributors

Become a financial contributor and help us sustain our community. More donation options are outlined on the [Donating](https://pywebview.flowrl.com/contributing/donating.html) page.


#### Individuals

<a href="https://opencollective.com/pywebview"><img src="https://opencollective.com/pywebview/individuals.svg?width=890"></a>

<a href="https://www.patreon.com/bePatron?u=13226105" data-patreon-widget-type="become-patron-button"><img src='https://c5.patreon.com/external/logo/become_a_patron_button.png' alt='Become a Patron!'/></a>


#### Organizations

Support this project with your organization. Your logo will show up here with a link to your website. [[Contribute](https://opencollective.com/pywebview/contribute)]

<a href="https://opencollective.com/pywebview/organization/0/website"><img src="https://opencollective.com/pywebview/organization/0/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/1/website"><img src="https://opencollective.com/pywebview/organization/1/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/2/website"><img src="https://opencollective.com/pywebview/organization/2/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/3/website"><img src="https://opencollective.com/pywebview/organization/3/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/4/website"><img src="https://opencollective.com/pywebview/organization/4/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/5/website"><img src="https://opencollective.com/pywebview/organization/5/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/6/website"><img src="https://opencollective.com/pywebview/organization/6/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/7/website"><img src="https://opencollective.com/pywebview/organization/7/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/8/website"><img src="https://opencollective.com/pywebview/organization/8/avatar.svg"></a>
<a href="https://opencollective.com/pywebview/organization/9/website"><img src="https://opencollective.com/pywebview/organization/9/avatar.svg"></a>

