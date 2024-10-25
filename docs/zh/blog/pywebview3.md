<img src='./pywebview3.png' alt='pywebview 3.0' style='max-width: 300px; margin: 50px auto; display: block'/>


# Introducing pywebview 3.0

I am happy to announce the release of _pywebview 3.0_. _pywebview_ lets you to build GUI for your Python program using HTML, CSS and Javascript, while doing its best  hiding the fact that the GUI is built using a browser. Think of _pywebview_ as lightweight Electron for Python. Unlike Electron, _pywebview_ does not bundle a web renderer, but instead relies on a rendered provided by operating system. _Sidenote: bundling a renderer is still an option though, as in case of CEF_.

If you are new here, head over to [usage guide](/guide/usage.html), [API reference](/guide/api.html), [examples](/examples) and our very own [TODOs app](https://github.com/r0x0r/pywebview/tree/master/examples/todos).

Oh and _pywebview_ can be installed with

``` bash
pip install pywebview
```


## What's new?

Version 3.0 is the first version that is not compatible with previous versions. Multi-window support introduced in 2.x resulted in some questionable architectural decisions, which now have been resolved and hopefully make more sense. Notable changes include:


### webview.start()
The biggest change is introduction of window objects and `webview.start()` function that starts a GUI loop. Previously GUI loop was started by the first call of `webview.create_window()`. Hence `create_window` had in fact two functions: creating a window and starting a GUI loop. To make things more confusing the first call to `create_window` was blocking, while subsequent calls from subthreads were not. To make things more straightforward, `create_window` now creates a window and returns a window object, no matter how many times you call it. The function is always non-blocking too. Bear in mind that until GUI loop is started, no windows are displayed. Using new API, hello world in _pywebview_ looks like this:

``` python
import webview

window = webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
webview.start()
```

`webview.start` also provides a convenient way to execute thread specific code after GUI loop is started, so no more threading boilerplate.

``` python
import webview

def change_title(window):
  window.change_title('pywebview whoa')

window = webview.create_window('pywebview wow', 'https://pywebview.flowrl.com/hello')
webview.start(change_title, window)
```


### Window object
All the functions related to window management and web content have been moved to a window object as returned by `webview.create_window`. For example `webview.load_html` became `window.load_html` as in:

``` python
import webview

def load_html(window):
  window.load_html('<html><body><h1>pywebview wow!</h1><body></html>')

window = webview.create_window('pywebview wow')
webview.start(load_html, window)
```



### Built-in HTTP server
_pywebview_ now provides its own HTTP server for serving static local files. For obfuscation purposes server is started on a random port.

``` python
import webview

window = webview.create_window('pywebview wow', 'assets/index.html')
webview.start(http_server=True)
```


### Events
3.0 introduces a new event system that lets to subscribe/unsubscribe to events. Currently `shown` and `loaded` events are implemented. Event objects are provided by a window object. See [events example](/examples/events.html) for usage details.


### Edge support
Windows now provides support for EdgeHTML. EdgeHTML is automatically chosen if your system requirements are met (.NET 4.6.2 and Windows 10 1803). Unfortunately accessing local files is not currently possible with EdgeHTML, so you must use a HTTP server. If you wish for some reason to force MSHTML, you can `webview.start(gui='mshtml')`.


### create_window now can load html directly

``` python
import webview

window = webview.create_window('pywebview wow', html='<html><body><h1>pywebview wow!</h1><body></html>')
webview.start()
```

If both url and html parameters are provided, html takes precedence.


### get_elements
You can now retrieve DOM nodes by using `window.get_elements(selector)` function. Nodes are serialized using [domJSON](https://github.com/azaslavsky/domJSON) library.

[Example](/examples/get_elements.html)

### Config is gone
`webview.config` is no more. To set a GUI renderer, use the `gui` parameter to `webview.start`


### confirm_quit is now confirm_close

E.g. `webview.create_window('Window', confirm_close=True)`


# Support the project

_pywebview_ is a small project with limited resources, any help is welcome. PRs, documentation, research, anything goes. Having said that commits are preferred over comments. Check out the [contributing guide](/contributing) to get started.

If you find _pywebview_ useful, please support it. We offer donations via Patreon and Open Collective, as well as one-time Paypal donations. If you represent a company, consider becoming a sponsor to get exposure for your company and connect with Python developers.

<div class="center spc-l spc-vertical">
	<a href="https://www.patreon.com/bePatron?u=13226105" data-patreon-widget-type="become-patron-button">
		<img src='https://c5.patreon.com/external/logo/become_a_patron_button.png' alt='Become a Patron!'/>
	</a>
</div>

<div class="center spc-l spc-vertical">
	<a href="https://opencollective.com/pywebview/donate" target="_blank">
		<img src="https://opencollective.com/pywebview/donate/button@2x.png?color=blue" width=300 />
	</a>
</div>

<div class="center spc-l spc-vertical">
	<a href="http://bit.ly/2eg2Z5P" target="_blank">
		<img src="/paypal.png"/>
	</a>
</div>
