<p align='center'><img src='assets/logo.png' width=480 alt='pywebview2 logo'/></p>

<p align='center'><a href="https://opencollective.com/pywebview" alt="Financial Contributors on Open Collective"><img src="https://opencollective.com/pywebview/all/badge.svg?label=financial+contributors" /></a> <img src="https://badge.fury.io/py/pywebview2.svg" alt="PyPI version" /> <img src="https://img.shields.io/pypi/dm/pywebview2" alt="PyPI downloads" /> <a href="https://github.com/imattau/pywebview2"><img src="https://img.shields.io/github/actions/workflow/status/imattau/pywebview2/ci.yml?branch=master" alt="Build status" /></a>

https://github.com/imattau/pywebview2
</p>

_pywebview2_ is a lightweight native webview wrapper that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. _pywebview2_ ships with a built-in HTTP server, DOM support in Python and window management functionality.

_pywebview2_ is available for Windows, macOS, Linux (GTK or QT) and Android. It uses native GUI for creating a web component window: WinForms on Windows, Cocoa on macOS and QT or GTK on Linux. If you choose to freeze your application, _pywebview2_ does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small.

_pywebview2_ provides advanced features like window manipulation functionality, event system, built-in HTTP server, native GUI elements like application menu and various dialogs, two way communication between Javascript ↔ Python and DOM support.

_pywebview2_ is developed on top of the original pywebview created by [Roman Sirokov](https://github.com/r0x0r/).


## Install

``` bash
pip install pywebview2
```

_You might need additional libraries. Refer to the documentation page for details._

## Hello world

``` python
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
webview.start()
```

Explore _pywebview2_ further by reading documentation, exploring [examples](https://github.com/imattau/pywebview2/tree/master/examples) or contributing.


## Sponsors

[![TestMu AI Sponsor](/assets/testmuai.svg)](https://www.testmuai.com/?utm_medium=sponsor&utm_source=pywebview)


## Code Contributors

This project thrives thanks to the contributions of our community. [[Learn how to contribute](docs/contributing/README.md)].

<a href="https://github.com/imattau/pywebview2/graphs/contributors"><img src="https://opencollective.com/pywebview/contributors.svg?width=890&button=false" /></a>

## Consulting services

If your company is looking for support with _pywebview2_ or needs a hand with full-stack development, the author of _pywebview_ is available for hire. As a VAT-registered EU based professional, I specialize in a wide range of technologies, including JavaScript/TypeScript, React/Vue, Python, GIS, SQL databases, API integration, CI/CD pipelines and cloud solutions. For inquiries about availability and pricing details, reach out to roman@maumau.fi.

## Donate

Become a financial contributor and help us sustain our community. More donation options are outlined on the [Donating](https://pywebview.flowrl.com/contributing/donating.html) page.

[![Github Sponsor](/docs/.vuepress/public/github_sponsor_button.png)](https://github.com/sponsors/r0x0r)

[![Patreon](/docs/.vuepress/public/patreon.png)](https://www.patreon.com/bePatron?u=13226105)

[![Open Collective](/docs/.vuepress/public/opencollective.png)](https://opencollective.com/pywebview/donate)
