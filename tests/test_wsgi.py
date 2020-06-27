import io
import wsgiref.util

from webview.wsgi import send_simple_text, Routing, StaticContentsApp


def make_wsgi_get(app, path):
    environ = {
        'SCRIPT_NAME': '',
        'PATH_INFO': path
    }
    wsgiref.util.setup_testing_defaults(environ)

    resp_status = None

    def sr(status, headers):
        nonlocal resp_status
        resp_status = status

    resp_body = b''.join(app(environ, sr))
    return resp_status, resp_body


def basic_app(response):
    def app(environ, start_response):
        return send_simple_text(environ, start_response, "200 OK", response)

    return app


def test_routing_simple():
    app = Routing({
        '/': basic_app("root"),
        '/spam': basic_app("spam"),
        '/eggs': basic_app("eggs"),
        '/spam/eggs': basic_app("vikings"),
    })

    assert make_wsgi_get(app, "/") == ('200 OK', b'root')
    assert make_wsgi_get(app, "/spam") == ('200 OK', b'spam')
    assert make_wsgi_get(app, "/eggs") == ('200 OK', b'eggs')
    assert make_wsgi_get(app, "/spam/eggs") == ('200 OK', b'vikings')
    assert make_wsgi_get(app, "/nope") == ('200 OK', b'root')


def test_routing_404():
    app = Routing({
        '/spam': basic_app("spam"),
        '/eggs': basic_app("eggs"),
    })

    assert make_wsgi_get(app, "/spam") == ('200 OK', b'spam')
    assert make_wsgi_get(app, "/eggs") == ('200 OK', b'eggs')
    assert make_wsgi_get(app, "/nope")[0] == '404 Not Found'


def test_basic_static():
    class Echo(StaticContentsApp):
        def open(self, path):
            return io.BytesIO(path.encode('utf-8'))

    app = Echo()

    assert make_wsgi_get(app, "/spam") == ('200 OK', b'/spam')
    assert make_wsgi_get(app, "/eggs") == ('200 OK', b'/eggs')
    assert make_wsgi_get(app, "/foo.txt") == ('200 OK', b'/foo.txt')
