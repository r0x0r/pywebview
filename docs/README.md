---
home: true
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
  - header: Current version
    description: 5.4
    #link: [What's new](/changelog.html)


    # image: /assets/image/box.svg
    # bgImage: https://theme-hope-assets.vuejs.press/bg/3-light.svg
    # bgImageDark: https://theme-hope-assets.vuejs.press/bg/3-dark.svg
    # highlights:
    #   - title: Run <code>pnpm create vuepress-theme-hope hope-project</code> to create a new project with this theme.
    #   - title: Run <code>pnpm create vuepress-theme-hope add .</code> in your project root to create a new project with this theme.


  - header: Features
    #image: /assets/image/markdown.svg
    bgImage: https://theme-hope-assets.vuejs.press/bg/2-light.svg
    bgImageDark: https://theme-hope-assets.vuejs.press/bg/2-dark.svg
    bgImageStyle:
      background-repeat: repeat
      background-size: initial
    features:
      - title: Cross-platform
        details: Available for Windows, macOS, Linux and Android
        icon: clipboard-check

      - title: Two-way Javav

      - title: Native components
        details: Menu, message and file boxes are native GUI

      - title: DOM support
        details: Manipulate and traverse DOM using Python API

      - title: Bundler friendly
        details: Supports pyinstaller and nuitka out of the box

---


_pywebview_ is a lightweight BSD-licensed cross-platform wrapper around a webview component. _pywebview_ allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. _pywebview_ ships with a built-in HTTP server, DOM support in Python and window management functionality.

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