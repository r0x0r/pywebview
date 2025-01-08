---
home: true
title: pywebview
tagline: Build GUI for your Python program with JavaScript, HTML, and CSS.
heroImage: logo.png
footer: BSD Licensed | Copyright © 2014–present Roman Sirokov
actions:
  - text: Get started
    icon: lightbulb
    link: /guide/
  - text: API
    icon: code
    link: /guide/api
  - text: Examples
    icon: star
    link: /examples/

highlights:
  - header: Features
    description: pywebview is a lightweight BSD-licensed cross-platform wrapper around a webview component. pywebview allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application,
   hiding the fact that GUI is browser based. pywebview ships with a built-in HTTP server, DOM support in Python and window management functionality.
    image: /assets/image/ui.svg
    # bgImage: https://theme-hope-assets.vuejs.press/bg/6-light.svg
    # bgImageDark: https://theme-hope-assets.vuejs.press/bg/6-dark.svg
    highlights:
      - title: Cross-platform
        details: Available for Windows, macOS, Linux and Android
        icon: clipboard-check

      - title: Two-way Javascript↔Python communication
        details: Communicate between Javascript and Python domains without HTTP

      - title: Built-in HTTP server
        details: Serve static files through built-in HTTP server

      - title: Native components
        details: Menu, message-boxes and file dialogs are native GUI elements.

      - title: DOM support
        details: Manipulate and traverse DOM nodes using Python API

      - title: Better filesystem support
        details: Get full path of dropped files

      - title: Bundler friendly
        details: Supports pyinstaller, nuitka and py2app
---



## Install

``` bash
pip install pywebview
```

_Depending on a platform you may need to install additional libraries. Refer to the [installation](/guide/installation.html) page for details._

## Hello world

``` python
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/')
webview.start()
```

Explore [documentation](/guide/) or [examples](/examples/). If React is your thing, get started right away with [React boilerplate](https://github.com/r0x0r/pywebview-react-boilerplate).

## Support the project

If you find _pywebview_ useful, please support it.

::: center
[![Github Sponsor](/github_sponsor_button.png)](https://github.com/sponsors/r0x0r)

[![Patreon](/patreon.png)](https://www.patreon.com/bePatron?u=13226105)

[![Open Collective](/opencollective.png)](https://opencollective.com/pywebview/donate)
:::