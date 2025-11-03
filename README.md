<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://opencollective.com/pywebview" alt="Financial Contributors on Open Collective"><img src="https://opencollective.com/pywebview/all/badge.svg?label=financial+contributors" /></a> <img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /> <img src="https://img.shields.io/pypi/dm/pywebview" alt="PyPI downloads" /> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd/branch/master?svg=true" alt="Build status" /></a>

https://pywebview.flowrl.com
</p>

_pywebview_ is a lightweight native webview wrapper that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. _pywebview_ ships with a built-in HTTP server, DOM support in Python and window management functionality.

_pywebview_ is available for Windows, macOS, Linux (GTK or QT) and Android. It uses native GUI for creating a web component window: WinForms on Windows, Cocoa on macOS and QT or GTK on Linux. If you choose to freeze your application, _pywebview_ does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small.

_pywebview_ provides advanced features like window manipulation functionality, event system, built-in HTTP server, native GUI elements like application menu and various dialogs, two way communication between Javascript ↔ Python and DOM support.

_pywebview_ is created by [Roman Sirokov](https://github.com/r0x0r/).


## Install

``` bash
pip install pywebview
```

_You might need additional libraries.  Refer to the [installation](https://pywebview.flowrl.com/guide/installation) page for details._

## Hello world

``` python
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
webview.start()
```

Explore _pywebview_ further by reading [documentation](https://pywebview.flowrl.com/guide), exploring [examples](https://pywebview.flowrl.com/examples) or [contributing](https://pywebview.flowrl.com/contributing). If React is your thing, get started right away with [React boilerplate](https://github.com/r0x0r/pywebview-react-boilerplate).


## Sponsors


<a href="https://www.lambdatest.com/?utm_source=pywebview&utm_medium=sponsor" target="_blank">
    <img src="https://www.lambdatest.com/blue-logo.png" style="vertical-align: middle; padding: 1rem 0 8rem 0;" width="250" height="45" />
</a><br/><br/>

## Code Contributors

This project thrives thanks to the contributions of our community. [[Learn how to contribute](docs/contributing/README.md)].

<a href="https://github.com/r0x0r/pywebview/graphs/contributors"><img src="https://opencollective.com/pywebview/contributors.svg?width=890&button=false" /></a>

## Consulting services

If your company is looking for support with _pywebview_ or needs a hand with full-stack development, the author of _pywebview_ is available for hire. As a VAT-registered EU based professional, I specialize in a wide range of technologies, including JavaScript/TypeScript, React/Vue, Python, GIS, SQL databases, API integration, CI/CD pipelines and cloud solutions. For inquiries about availability and pricing details, reach out to roman@maumau.fi.

## Donate

Become a financial contributor and help us sustain our community. More donation options are outlined on the [Donating](https://pywebview.flowrl.com/contributing/donating.html) page.

[![Github Sponsor](/docs/.vuepress/public/github_sponsor_button.png)](https://github.com/sponsors/r0x0r)

[![Patreon](/docs/.vuepress/public/patreon.png)](https://www.patreon.com/bePatron?u=13226105)

[![Open Collective](/docs/.vuepress/public/opencollective.png)](https://opencollective.com/pywebview/donate)
