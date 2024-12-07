# Security

When using a local web server, you may want to protect your API from unauthorized access.

First, it is advisable to enable SSL for local http server. To accomplish this, simply start the application with the `ssl` paramater set to True `webview.start(ssl=True)`.

Second, if you use a third party http server with REST API, [CSRF attacks](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)) can be a major problem. _pywebview_ addresses the problem by generating a session-unique token that is exposed both to Python as `webview.token` and Javascript as `window.pywebview.token`. Refer to [CSRF cheat sheet](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_\(CSRF\)_Prevention_Cheat_Sheet) for API securing approaches and see [Flask app](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app) for a concrete example.
