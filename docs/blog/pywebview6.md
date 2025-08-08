<img src='/logo-no-text.png' alt='pywebview' style='max-width: 150px; margin: 50px auto 20px auto; display: block'/>


# 6.0 is here

I am excited to announce the release of _pywebview 6_. The new version introduces powerful state management, network event handling, and significant improvements to Android support. For a complete changelog, see [here](/changelog).

If you are not familiar with _pywebview_, it's a lightweight Python framework for building modern desktop applications with web technologies. Unlike heavyweight alternatives, _pywebview_ leverages your system's native webview, resulting in smaller binaries and better performance. Write your UI once in HTML, CSS, and JavaScript, then deploy across Windows, macOS, Linux, and Android with the full power of Python at your fingertips. _pywebview_ can be installed with

``` bash
pip install pywebview
```

## Shared State Management

One of the most exciting features in version 6 is the new shared state management via the `window.state` object. This revolutionary feature automatically synchronizes state between Javascript and Python, eliminating the need for manual data synchronization.

``` python
# In Python
window.state.user_name = "Test"
```

``` javascript
// In Javascript - automatically updated!
console.log(window.pywebview.state.user_name); // "Test"
```

This bidirectional synchronization makes building complex applications much simpler, as you no longer need to manually pass data between Python and Javascript. Currenlty state syncronization is limited to top-level properties. If you want to synchronize nested objects, you need to reassign the entire object. For example:

``` python
# In Python
window.state.user_settings = {"theme": "dark", "notifications": True}
```

``` javascript
// In Javascript - automatically updated!
console.log(window.pywebview.state.user_settings); // {"theme": "dark", "notifications": True}
window.pywebview.state.user_settings = {"theme": "light", "notifications": False} // Updates Python side too
```

## New events

_pywebview 6_ introduces powerful network monitoring capabilities with the new `request_sent` and `response_received` events. These events are fired whenever HTTP requests are made, giving you full visibility into your application's network activity. Request headers can be modified before sending, and you can inspect responses as they arrive. Response header modification is not supported.

``` python
def on_request_sent(request):
    print(f"Sending request to: {request['url']}")
    # Modify request headers before sending
    request['headers']['Authorization'] = f"Bearer {get_auth_token()}"

def on_response_received(response):
    print(f"Received response: {response['status_code']}")

window.events.request_sent += on_request_sent
window.events.response_received += on_response_received
```

Another new event is `initialized`, which is fired when the GUI library or webview renderer is chosen, before the window is created. This allows you to customize behavior based on the selected renderer or abort execution altogether by returning `False` from the event handler.

``` python
def on_initialized(renderer):
    print(f"Initialized with renderer: {renderer}")

window.events.initialized += on_initialized
```

## Enhanced Android Support

Android support receives a major upgrade with a new Kivyless implementation that significantly improves startup time and reduces package size. Additionally, Android apps now support fullscreen mode, bringing mobile experience closer to native apps.

Furthermore Android now has a new dedicated test suite found in `tests/android`.

## Window-Specific Menus

You can now create custom menus for individual windows, giving you more control over the user interface (not supported on GTK with Unity)

``` python
menu = webview.menu.Menu([
    webview.menu.MenuAction('File', [
        webview.menu.MenuAction('New', new_file),
        webview.menu.MenuSeparator(),
        webview.menu.MenuAction('Exit', exit_app)
    ])
])

window = webview.create_window('My App', 'index.html', menu=menu)
```

## Modern API Improvements

Version 6 includes several breaking changes that modernize the API and removes deprecated features:

- File dialog constants are now part of the `webview.FileDialog` enum (`SAVE`, `LOAD`, `FOLDER`)
- `webview.DRAG_REGION_SELECTOR` moved to `webview.settings['webview.DRAG_REGION_SELECTOR']`
- Deprecated DOM functions are removed in favor of the modern `window.dom` API


## Platform-Specific Enhancements

- **Windows**: Dark mode support with automatic theme detection
- **macOS**: Option to hide default menus and better Javascript prompt handling
- **All platforms**: Improved screen coordinate handling and better SSL support

## Learn more

Ready to explore _pywebview 6_? Check out the [usage guide](/guide/usage.html), [API reference](/guide/api.html) and [examples](/examples) to get started with the new features.

## Support the project

_pywebview_ continues to be primarily a one-person project, updated when time allows. Your contributions make a real difference! The best way to help is by submitting pull requests - bug fixes are always welcome, and for new features, please create an issue to discuss first. Check out the [contributing guide](/contributing) to get started.

If _pywebview_ has been useful for your projects and you'd like to see continued development, consider sponsoring the project. Companies can become sponsors to gain exposure and connect with the Python developer community.

<div class="center spc-l spc-vertical">
	<a href="https://github.com/sponsors/r0x0r">
		<img src='/github_sponsor_button.png' alt='Sponsor on Github' style="max-width: 250px"/>
	</a>
</div>

<div class="center spc-l spc-vertical">
	<a href="https://opencollective.com/pywebview/donate" target="_blank">
		<img src="https://opencollective.com/pywebview/donate/button@2x.png?color=blue" width=300 />
	</a>
</div>

<div class="center spc-l spc-vertical">
	<a href="https://www.patreon.com/bePatron?u=13226105" data-patreon-widget-type="become-patron-button">
		<img src='https://c5.patreon.com/external/logo/become_a_patron_button.png' alt='Become a Patron!'/>
	</a>
</div>

<div class="center spc-l spc-vertical">
	<a href="http://bit.ly/2eg2Z5P" target="_blank">
		<img src="/paypal.png"/>
	</a>
</div>