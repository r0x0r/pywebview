# Application architecture

There are two ways to build your application using _pywebview_:

- By using JS API bridge and serving static content with a built-in HTTP server. JS API bridge can be created either with `create_window(..., js_api=Api())` or or `window.expose` function. To serve static contents, set entrypoint url to a local relative path. This will start a built-in HTTP server automatically. For communication between Python and Javascript refer to [interdomain communication](/guide/interdomain.html). See an example [serverless application](https://github.com/r0x0r/pywebview/tree/master/examples/todos) for a complete implementation.

You can also load HTML directly without a HTTP server using `webview.create_window(...html='')` or `window.load_html`. This approach has got limitations though, as file system does not exist in the context of the loaded page. Images and other assets can be loaded only inline using Base64.

- By running a separate local web server. This way static assets and REST endpoints are served from the same server. When using a local web server, you should protect your API calls against CSRF attacks. See [security](/guide/security.html) for more information. See an example [Flask-based application](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app)

