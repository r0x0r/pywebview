# 使用

## 基础

一个最小的使用 _pywebview_ 的程序是这样的：

``` python
import webview

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
webview.start()
```
`create_window`函数会创建一个新窗口并返回一个`window`对象实例。如果是在`webview.start()`前创建的窗口，则会等到GUI循环启动后显示，在`webview.start()`则会立即显示。

您可以创建任意数量的窗口。所有打开的窗口都以列表形式存储在“webview.windows”中。窗口按创建顺序存储。

``` python
import webview

first_window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
second_window = webview.create_window('Second window', 'https://woot.fi')
webview.start()
```

_pywebview_ 提供了多个web渲染器的选择。要更改web渲染器，请将“start”函数的“gui”参数设置为所需值（例如“cef”或“qt”）。有关详细信息，请参见[渲染器]（/zh/guide/Renderer.md）。

## 后端逻辑

`webview.start`启动一个GUI循环，并阻止进一步的代码执行，直到最后一个窗口被销毁。由于GUI循环被阻塞，您必须在单独的线程或进程中执行后端逻辑。您可以通过将函数传递给`webview.start(func, (params,))`来执行后端代码。这将启动一个单独的线程，与手动启动线程相同。

``` python
import webview

def custom_logic(window):
    window.toggle_fullscreen()
    window.evaluate_js('alert("Nice one brother")')

window = webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start(custom_logic, window)
# 此行以下的任何内容都将在程序执行完毕后执行
pass
```

## Javascript与Python之间的通信

要从Python运行Javascript，请使用`window.evaluate_js(code)`。该函数返回Javascript代码中最后一行的结果。如果代码返回一个promise，你可以通过传递一个回调函数`window.evaluate_js(code，callback)`来解决它。如果Javascript抛出错误，`window.evaluate_js`将引发一个`webview.errors.JavascriptException`异常。

要从Javascript运行Python，您需要使用`webview.create_window(url, js_api=api_instance)`以公开API类。类成员函数将在Javascript域中以`window.pywebview.api.funcName`的形式提供。您也可以在运行时使用`window.expose(func)`公开单个函数。有关详细信息，请参阅[域间通信](/zh/guide/interdomain.md)。

``` python
import webview

class Api():
  def log(self, value):
    print(value)

webview.create_window("Test", html="<button onclick='pywebview.api.log(\"Woah dude!\")'>Click me</button>", js_api=Api())
webview.start()
```

或者，您可以使用一种更传统的方法，将REST API与WSGI服务器配对用于域间通信。请参阅[Flask应用程序](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app)。

## HTTP服务器

_pywebview_ 内部使用[bottle.py](https://bottlepy.org)作为提供静态文件的HTTP服务器。相对本地路径由内置的HTTP服务器提供服务。入口点目录充当HTTP服务器根目录，目录下的所有内容及其目录都是共享的。您可以通过设置`webview.start(ssl=True)`为服务器启用SSL。

``` python
import webview

webview.create_window('Woah dude!', 'src/index.html')
webview.start(ssl=True)
```

如果您希望使用与WSGI兼容的外部HTTP服务器，可以将服务器应用程序对象作为URL传递。

``` python
from flask import Flask
import webview

server = Flask(__name__, static_folder='./assets', template_folder='./templates')
webview.create_window('Flask example', server)
webview.start()
```

如果你的目的是在没有HTTP服务器的情况下使用`file://`协议来提供文件，你可以通过使用绝对文件路径或在路径前加上`file://'协议来实现。

``` python
import webview

# 它将在 file:///home/pywebview/project/index.html 上服务
webview.create_window('Woah dude!', '/home/pywebview/project/index.html')
webview.start()
```

### 加载 HTML

Alternatively, you can load HTML by setting the `html` parameter or with `window.load_html` function. A limitation of this approach is that but file system does not exist in the context of the loaded page. Images and other assets can be loaded only inline using Base64.
或者，您可以通过设置`html`参数或使用`window.load_html`函数来加载HTML。这种方法的一个局限性是，在加载的页面上下文中不存在文件系统。图像和其他资源只能使用Base64内联加载。

``` python
import webview

webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start()
```
