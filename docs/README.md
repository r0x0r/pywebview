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
    link: /api/
  - text: Examples
    icon: star
    link: /examples/

---
<CurrentVersion version="6.1"/>

_pywebview_ is a lightweight BSD-licensed cross-platform wrapper around a webview component. _pywebview_ allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. _pywebview_ ships with a built-in HTTP server, DOM support in Python and window management functionality.,


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

<Features/>



::: center
[![Github Sponsor](/github_sponsor_button.png)](https://github.com/sponsors/r0x0r)

[![Patreon](/patreon.png)](https://www.patreon.com/bePatron?u=13226105)

[![Open Collective](/opencollective.png)](https://opencollective.com/pywebview/donate)
:::
