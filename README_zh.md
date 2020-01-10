<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://opencollective.com/pywebview" alt="Financial Contributors on Open Collective"><img src="https://opencollective.com/pywebview/all/badge.svg?label=financial+contributors" /></a> <img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /> <a href="https://travis-ci.org/r0x0r/pywebview"><img src="https://travis-ci.org/r0x0r/pywebview.svg?branch=master" alt="Build Status" /></a> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd/branch/master?svg=true" alt="Build status" /></a>

https://pywebview.flowrl.com
</p>

[English](README.md) | [简体中文](README_zh.md)

_pywebview_ 是一个轻量级、跨平台的组件库，允许你在原生 GUI 窗口中展示 HTML 内容。它基于一个隐藏的浏览器环境，给你在桌面应用中提供使用 web 技术的能力。 你可以在使用 pywebview 的同时使用其他的轻量级框架比如： [Flask](http://flask.pocoo.org/) 或者 [Bottle](http://bottlepy.org/docs/dev/index.html) 或者其他网页框架。

_pywebview_ 使用原生 GUI 创建包含网页内容的窗口: 在  Windows 平台上是 WinForms ,在 macOS 使用 Cocoa ，在Linux使用 QT 或者 GTK . 如果你打包你的应用, pywebview 不会受到沉重的 GUI 工具和网页渲染器的约束，因此它可以保证你最终生成的可执行文件体积小. _pywebview_ 兼容 Python 2 和 Python 3.

_pywebview_ 由 [Roman Sirokov](https://github.com/r0x0r/)开发. 由 Roman 和 [Shiva Prasad](https://github.com/shivaprsdv)维护.


# 开始使用

### 安装

``` bash
pip install pywebview
```
_在 Linux平台上，你可能需要安装额外的库. 在 [installation](https://pywebview.flowrl.com/guide/installation.html) 获取更多细节._


### Hello world
``` python
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
webview.start()
```

你可以通过阅读 [文档](https://pywebview.flowrl.com/guide), [案例](https://pywebview.flowrl.com/examples) 来了解更多，你也可以参与到我们的项目中，[贡献](https://pywebview.flowrl.com/contributing) 你的力量.



# Contributors 贡献者

### Code Contributors 代码贡献者

这个项目离不开这些 [贡献者们](CONTRIBUTING.md).
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

