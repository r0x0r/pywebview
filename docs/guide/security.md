# Security

When using a local web server, you must protect your API from unauthorized access. [CSRF attacks](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)) can be a major problem if API is not protected in an adequate matter. _pywebview_ generates a session-unique token that is exposed both to Python `webview.token` and DOM `window.pywebview.token`. See [Flask app](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app) for an example.

For building a custom solution refer to [this document](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_\(CSRF\)_Prevention_Cheat_Sheet) for API securing approaches. A library like [flask-seasurf](https://flask-seasurf.readthedocs.io/en/latest/) alongside Flask can be used too.