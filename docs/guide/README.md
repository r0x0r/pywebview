# Introduction

_pywebview_ is a lightweight native webview wrapper that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. _pywebview_ ships with a built-in HTTP server, DOM support in Python and window management functionality.

_pywebview_ is available for Windows, macOS, Linux (GTK or QT) and Android. It uses native GUI for creating a web component window: WinForms on Windows, Cocoa on macOS and QT or GTK on Linux. If you choose to freeze your application, _pywebview_ does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small.

_pywebview_ provides advanced features like window manipulation functionality, event system, built-in HTTP server, native GUI elements like application menu and various dialogs, two way communication between Javascript ↔ Python and DOM support.

_pywebview_ is created by [Roman Sirokov](https://github.com/r0x0r/).

## Install

Generally, you should be able to install _pywebview_ with

``` bash
pip install pywebview
```

Although on some Linux platforms you may need to install additional libraries. Refer to the [installation](/guide/installation.html) page for details.

## Develop

Read the basic concepts in [Usage](/guide/usage), dive into [application architecture](/guide/architecture). Explore [API](/guide/api) and check various [examples](/examples)

## Contribute

Checkout out [contributing guidelines](/contributing)

## Support the project

If you find _pywebview_ useful, please support it.

::: center
[![Github Sponsor](/github_sponsor_button.png)](https://github.com/sponsors/r0x0r)

[![Patreon](/patreon.png)](https://www.patreon.com/bePatron?u=13226105)

[![Open Collective](/opencollective.png)](https://opencollective.com/pywebview/donate)
:::