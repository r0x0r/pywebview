<img src='/logo-no-text.png' alt='pywebview' style='max-width: 150px; margin: 50px auto 20px auto; display: block'/>


# 5.0 has landed

I am happy to announce the release of _pywebview 5_. The new version introduces three major features: Android support, DOM manipulation and application settings. For a full changelog, see [here](/changelog).

If you are not familiar with _pywebview_, it is a Python library that lets you to build GUI for your Python program using HTML, CSS and Javascript. Available for Windows, macOS, Linux and Android. _pywebview_ can be installed with

``` bash
pip install pywebview
```

## Android

You can now run your _pywebview_ on Android devices. Mobile experience brings its own limitations though. There is no window manipulation, multi-window or file dialog support. Otherwise, it works same as on other platforms. Head over to [Freezing](/guide/freezing.md) for details how to package your app for Android.

## DOM

With DOM support you can perform jQuery like DOM manipulation, traversal and event handling straight from Python. You can access and modify element's attributes, style and classes as well. A new `Element` object represents a DOM node in Python. It is returned by `window.dom.get_element`, `window.dom.get_elements` and `window.dom.create_element`. Body, document and window are conviently exposed as `window.dom.body`, `window.dom.document` and `window.dom.body` respectively. The new Javascript serializer allows you to serialize more Javascript object types and handles circular dependencies, so

Here is a toy example of the new API.

``` python
window.dom.document.events.scroll += lambda e: print(window.dom.window.node['scrollY'])

button = window.dom.create_element('<button disabled class="hidden">Button</button>', window.dom.body)
button.style['width'] = '200px'
button.attributes = { 'disabled': False }
button.events.click += click_handler
button.classes.toggle('hidden')
```

See [events](/examples/dom_events.md), [manipulation](/examples/dom_manipulation.md), [events](/traversal/dom_traversal.md) for complete examples.

A much requested feature is a full file path support for drag and drop operations. _pywebview_ enhances `DropEvent` by introducing `event['dataTransfer']['files'][0]['pywebviewFullPath']` that has full absolute path of a dropped file(s). The full path is available only on Python's side.

## Application settings

_pywebview_ is rather opinionated on how default experience should be. Over the years, I have received numerous feature requests asking to change the default behaviour, which is now possible with application settings. The new version introduces `webview.settings` dictionary with following options.

``` python
webview.settings = {
    'ALLOW_DOWNLOADS': False, # Allow file downloads
    'ALLOW_FILE_URLS': True, # Allow access to file:// urls
    'OPEN_EXTERNAL_LINKS_IN_BROWSER': True, # Open target=_blank links in an external browser
    'OPEN_DEVTOOLS_IN_DEBUG': True, # Automatically open devtools when `start(debug=True)`.
}
```

Application settings must be set before invoking `webview.start()` to have an effect.


## Learn more

Interested in learning more? Head over to [usage guide](/guide/usage.html), [API reference](/api.html) and [examples](/examples)


## Support the project

_pywebview_ is largely an one-man project, which gets updated sporadically whenever time permits. Any help is appreciated and the best way to contribute is submitting a pull request. Bug fixes are always welcomed. If you wish to submit a new feature, please create an issue and discuss it beforehand. Check out the [contributing guide](/contributing) to get started.

If you find _pywebview_ useful and would like to see it developed in the future, considering sponsoring it. If you represent a company, consider becoming a sponsor to get exposure for your company and connect with Python developers.

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
