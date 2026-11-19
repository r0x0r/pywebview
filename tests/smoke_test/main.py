import asyncio
import logging
import random
import threading
import time
from urllib.parse import urljoin, urlparse

from bottle import Bottle, static_file
from bottle import request as bottle_request

import webview
from webview.menu import Menu, MenuAction
from webview.util import get_app_root

logger = logging.getLogger('pywebview')

app = Bottle()

# Requests and responses of the local server seen by the window events, and the X-Smoke header
# that the server received on each path
network = {'requests': [], 'responses': [], 'hits': {}}


def record_hit(path):
    network['hits'].setdefault(path, []).append(bottle_request.headers.get('X-Smoke'))


@app.route('/')
def index():
    record_hit('/')
    resp = static_file('index.html', root=get_app_root())
    # secure=True would require HTTPS, but the local server runs over plain HTTP (see
    # webview.start() call below), so the browser would silently refuse to store it.
    resp.set_cookie('serverCookie', 'test', httponly=True)
    return resp


@app.route('/smoke/<name>')
def smoke(name):
    record_hit(f'/smoke/{name}')
    return {'name': name}


@app.route('/<filename:path>')
def static_files(filename):
    resp = static_file(filename, root=get_app_root())

    if filename.endswith('index.html'):
        logger.debug(f'Serving {filename} with serverCookie set')
        resp.set_cookie('serverCookie', 'test', httponly=True)

    return resp


class TestAPI:
    def getRandomNumber(self):
        return random.randint(0, 100)

    def sayHelloTo(self, name):
        return {'message': f'Hello {name}!'}

    def error(self):
        raise Exception('This is a Python exception')

    def getInteger(self):
        return 420

    def getString(self):
        return 'This is a string from Python'

    def getFloat(self):
        return 4.20

    def getList(self):
        return [1, 2, 3, 4, 5]

    def getNone(self):
        return None

    def getDict(self):
        return {'key1': 'value1', 'key2': 'value2'}


def wait_for(event, name, trigger, timeout=5):
    """Run trigger() and wait until the window event fires. Return the event arguments."""
    fired = threading.Event()
    args = []

    def handler(*event_args):
        args.extend(event_args)
        fired.set()

    event += handler
    try:
        trigger()
        if not fired.wait(timeout):
            raise TimeoutError(f'{name} event was not fired within {timeout}s')
    finally:
        event -= handler
    return args


def evaluate_promise(window, script, timeout=5):
    """Evaluate a script returning a promise and wait for the resolved value."""
    result = []
    done = threading.Event()

    def callback(value):
        result.append(value)
        done.set()

    window.evaluate_js(script, callback)
    if not done.wait(timeout):
        raise TimeoutError('evaluate_js callback was not called')
    return result[0]


OPTIONS_HTML = """
<html>
<head><title>Window options</title></head>
<body style="background: transparent">
    <div class="pywebview-drag-region" style="padding: 1rem">Drag region</div>
</body>
</html>
"""

OPTIONS_PROBE = """
var style = getComputedStyle(document.body);
({inner: [innerWidth, innerHeight], select: style.userSelect || style.webkitUserSelect})
"""


INSPECTION_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Window options</title>
<style>
    * { box-sizing: border-box; }
    html, body { margin: 0; height: 100%; background: transparent; }
    body {
        font: 14px/1.5 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
        color: #e5e7eb;
        display: flex;
        flex-direction: column;
    }
    .pywebview-drag-region {
        padding: 10px 14px;
        background: rgba(62, 175, 124, 0.85);
        color: white;
        font-weight: 600;
        cursor: grab;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    main {
        flex: 1;
        margin: 16px;
        padding: 16px;
        border-radius: 12px;
        background: rgba(17, 24, 39, 0.55);
        display: grid;
        gap: 10px;
        align-content: start;
    }
    .see-through {
        flex: none;
        height: 96px;
        margin: 0 16px 16px;
        border: 2px dashed rgba(229, 231, 235, 0.8);
        border-radius: 12px;
        display: grid;
        place-items: center;
        padding: 0 16px;
        text-align: center;
        font-weight: 600;
        color: white;
        text-shadow: 0 1px 3px black;
    }
    code { font-family: ui-monospace, Menlo, Consolas, monospace; color: #9ca3af; }
    button, input { font: inherit; }
    button {
        padding: 4px 12px;
        border: 0;
        border-radius: 6px;
        background: white;
        color: #111827;
        cursor: pointer;
    }
    input { padding: 6px 8px; border-radius: 6px; border: 1px solid #4b5563; }
    a { color: #6ee7b7; }
</style>
</head>
<body>
    <div class="pywebview-drag-region">
        Drag region: drag the window from here
        <button onclick="pywebview.api.close()">Close</button>
    </div>
    <main>
        <div><code>easy_drag</code> On a frameless window, drag from anywhere.</div>
        <div><code>background_color</code> Shows outside this panel and while the page loads.</div>
        <div><code>transparent</code> <code>vibrancy</code> The desktop shows, or is blurred,
            in the dashed area below and dimly behind this panel.</div>
        <div><code>zoomable</code> Pinch or Ctrl + scroll to zoom this text.</div>
        <div><code>draggable</code> Try dragging the image and the link:
            <img width="24" height="24" style="vertical-align: middle" alt="logo"
                src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect width='24' height='24' rx='6' fill='%233eaf7c'/%3E%3C/svg%3E">
            <a href="https://pywebview.flowrl.com">pywebview.flowrl.com</a></div>
        <div><code>focus</code> Typing should go here if the window took focus:
            <input autofocus placeholder="type here"></div>
        <div><code>shadow</code> Look for the shadow and rounded corners around the window.</div>
        <div><code>options</code> <span id="options"></span></div>
    </main>
    <div class="see-through">No background here: with transparent, the desktop shows through.
        Otherwise this is background_color.</div>
</body>
</html>
"""


class InspectionAPI:
    _window = None

    def close(self):
        self._window.destroy()


class WindowAPI:
    """Window functions called from tests/test-window-functions.js."""

    _window = None

    def info(self):
        return {
            'renderer': webview.renderer,
            'token': webview.token,
            'screens': len(webview.screens),
            'windows': len(webview.windows),
        }

    def set_title(self, title):
        old_title = self._window.title
        self._window.title = title
        new_title = self._window.title
        self._window.title = old_title
        return new_title

    def resize(self, width, height):
        w = self._window
        # Resizing to the current size fires no resized event, so use another size
        if abs(w.width - width) < 20 and abs(w.height - height) < 20:
            width, height = width + 100, height + 100
        args = wait_for(w.events.resized, 'resized', lambda: w.resize(width, height))
        return {'event': args, 'size': [w.width, w.height], 'target': [width, height]}

    def move(self, x, y):
        w = self._window

        def wait_for_position(x, y):
            # GTK fires moved on every configure, which can come before the move itself lands
            for _ in range(20):
                if abs(w.x - x) < 20 and abs(w.y - y) < 40:
                    break
                time.sleep(0.1)

        original = (w.x, w.y)
        # Moving to the current position fires no moved event, so go somewhere else
        if abs(w.x - x) < 20 and abs(w.y - y) < 40:
            x, y = x + 100, y + 100
        args = wait_for(w.events.moved, 'moved', lambda: w.move(x, y))
        wait_for_position(x, y)
        position = [w.x, w.y]
        # Restore the position, so the next run moves the window and gets a moved event
        w.move(*original)
        wait_for_position(*original)
        return {'event': args, 'position': position, 'target': [x, y]}

    def minimize_restore(self):
        w = self._window
        wait_for(w.events.minimized, 'minimized', w.minimize)
        wait_for(w.events.restored, 'restored', w.restore)
        return True

    def maximize_restore(self):
        w = self._window
        before = [w.width, w.height]
        wait_for(w.events.maximized, 'maximized', w.maximize)
        maximized = [w.width, w.height]
        wait_for(w.events.restored, 'restored', w.restore)
        return {'before': before, 'maximized': maximized}

    def toggle_fullscreen(self):
        w = self._window
        before = [w.width, w.height]
        w.toggle_fullscreen()
        time.sleep(1.5)  # macOS animates the transition
        fullscreen = [w.width, w.height]
        w.toggle_fullscreen()
        time.sleep(1.5)
        return {'before': before, 'fullscreen': fullscreen, 'after': [w.width, w.height]}

    def on_top(self):
        w = self._window
        w.on_top = True
        enabled = w.on_top
        w.on_top = False
        return [enabled, w.on_top]

    def hide_show(self):
        self._window.hide()
        time.sleep(0.5)
        self._window.show()
        return True

    def toggle_fullscreen_once(self):
        self._window.toggle_fullscreen()

    def open_with(self, options, action=None):
        """
        Open a window with create_window options, optionally restore or show it, and return its
        geometry and a probe of the page. The window is closed afterwards.
        """
        if 'min_size' in options:
            options['min_size'] = tuple(options['min_size'])

        window = webview.create_window(
            'Window options', html=OPTIONS_HTML, **{'width': 400, 'height': 300, **options}
        )
        try:
            if not window.events.loaded.wait(10):
                raise TimeoutError('Window did not load')
            time.sleep(1.5 if options.get('fullscreen') else 0.5)  # let geometry settle

            if action == 'restore':
                wait_for(window.events.restored, 'restored', window.restore)
            elif action == 'show':
                window.show()
                time.sleep(0.5)

            probe = window.evaluate_js(OPTIONS_PROBE)
            screen = webview.screens[0]
            return {
                'size': [window.width, window.height],
                'position': [window.x, window.y],
                'on_top': window.on_top,
                'inner': probe['inner'],
                'select': probe['select'],
                'screen': [screen.width, screen.height],
            }
        finally:
            closed = threading.Event()
            window.events.closed += closed.set
            window.destroy()
            closed.wait(5)

    def open_for_inspection(self, options):
        """Open a window with create_window options and leave it open for manual inspection."""
        api = InspectionAPI()
        window = webview.create_window(
            'Window options', html=INSPECTION_HTML, js_api=api, width=520, height=580, **options
        )
        api._window = window

        def show_options():
            enabled = ', '.join(f'{key}={value}' for key, value in options.items())
            window.dom.get_element('#options').text = enabled

        window.events.loaded += show_options

    def get_current_url(self):
        return self._window.get_current_url()

    def load_css(self):
        self._window.load_css(':root { --pywebview-css-probe: 42; }')

    def evaluate_js_promise(self):
        return evaluate_promise(
            self._window,
            'new Promise(function(resolve) { setTimeout(function() { resolve(42) }, 100) })',
        )

    def evaluate_js_exception(self):
        try:
            self._window.evaluate_js('throw new TypeError("smoke test error")')
        except webview.JavascriptException as e:
            return str(e)
        return None

    def python_state(self, key, value):
        """Set state from Python and return what Javascript sees."""
        self._window.state[key] = value
        time.sleep(0.2)
        return self._window.evaluate_js(f'window.pywebview.state[{key!r}]')

    def second_window(self):
        """Open a second window, talk to it, navigate it and close it."""
        second = webview.create_window(
            'Second window',
            html='<html><head><title>second</title></head><body>second window</body></html>',
            js_api=TestAPI(),
            width=400,
            height=300,
        )
        closed = threading.Event()
        second.events.closed += closed.set
        try:
            if not second.events.loaded.wait(10):
                raise TimeoutError('Second window did not load')

            title = second.evaluate_js('document.title')
            api_result = evaluate_promise(second, 'pywebview.api.getInteger()')
            count = len(webview.windows)

            wait_for(
                second.events.loaded,
                'loaded',
                lambda: second.load_html('<html><head><title>reloaded</title></head></html>'),
            )
            reloaded_title = second.evaluate_js('document.title')

            second.destroy()
            if not closed.wait(5):
                raise TimeoutError('closed event was not fired for the second window')
        finally:
            # Do not leave the window open when a step fails
            if not closed.is_set():
                second.destroy()

        return {
            'title': title,
            'api': api_result,
            'windows': count,
            'reloaded_title': reloaded_title,
            'windows_after': len(webview.windows),
        }

    def confirmation_dialog(self):
        return self._window.create_confirmation_dialog('pywebview', 'Did this dialog open?')

    def file_dialog(self, dialog_type):
        types = {
            'open': webview.FileDialog.OPEN,
            'folder': webview.FileDialog.FOLDER,
            'save': webview.FileDialog.SAVE,
        }
        result = self._window.create_file_dialog(
            types[dialog_type], allow_multiple=dialog_type == 'open', save_filename='smoke.txt'
        )
        return list(result) if result else None


class DomAPI:
    """Python DOM API calls from tests/test-dom.js. Each works inside #dom-sandbox."""

    _window = None

    def create_and_query(self):
        dom = self._window.dom
        sandbox = dom.get_element('#dom-sandbox')
        sandbox.empty()
        dom.create_element('<ul id="dom-list"></ul>', sandbox)
        dom_list = dom.get_element('#dom-list')
        for i in range(3):
            dom_list.append(f'<li class="dom-item">item {i}</li>')

        items = dom.get_elements('.dom-item')
        return {
            'count': len(items),
            'children': len(dom_list.children),
            'tag': items[0].tag,
            'text': items[1].text,
            'parent': items[0].parent.id,
            'next': items[0].next.text,
            'previous': items[2].previous.text,
        }

    def manipulate(self):
        dom = self._window.dom
        element = dom.create_element('<div id="dom-target">before</div>', '#dom-sandbox')
        element.text = 'after'
        element.classes.append('dom-class')
        element.style['color'] = 'rgb(255, 0, 0)'
        element.attributes['data-smoke'] = 'yes'
        element.hide()
        hidden = element.visible
        element.show()
        copy = element.copy(id='dom-copy')

        result = self._window.evaluate_js("""
            var el = document.getElementById('dom-target');
            ({
                text: el.textContent,
                hasClass: el.classList.contains('dom-class'),
                color: el.style.color,
                attribute: el.getAttribute('data-smoke'),
                copy: !!document.getElementById('dom-copy'),
            })
        """)
        result['hidden'] = hidden is False
        result['visible'] = element.visible
        copy.remove()
        result['copy_removed'] = dom.get_element('#dom-copy') is None
        return result

    def events(self):
        dom = self._window.dom
        button = dom.create_element('<button id="dom-button">click</button>', '#dom-sandbox')
        received = []
        clicked = threading.Event()

        def on_click(e):
            received.append(e['target']['id'])
            clicked.set()

        button.events.click += on_click
        self._window.run_js('document.getElementById("dom-button").click()')
        fired = clicked.wait(5)
        button.events.click -= on_click
        button.remove()
        return {'fired': fired, 'target': received[0] if received else None}


def exposed_function(value):
    return f'exposed {value}'


class NetworkAPI:
    _window = None

    def support(self):
        """What the request_sent and response_received events cover on this backend."""
        renderer = webview.renderer
        requests = renderer not in ('cef', 'qtwebkit')
        responses = requests
        if renderer == 'qtwebengine':
            from qtpy import QT_VERSION

            responses = tuple(int(v) for v in QT_VERSION.split('.')[:2]) >= (6, 6)
        # Android does not report responses or use modified headers for loopback URLs, which
        # include the built-in server
        android = renderer == 'android-webkit'
        every_request = renderer in ('edgechromium', 'winui3', 'qtwebengine', 'android-webkit')
        return {
            'request': requests,
            'response': responses and not android,
            'subresource_request': requests and renderer != 'wkwebview',
            'subresource_response': responses and not android and renderer != 'qtwebengine',
            'headers': requests and not android,
            'subresource_headers': every_request and not android,
            'subresource_cancel': every_request,
            'navigation_cancel': requests and not android,
        }

    def log(self):
        return network

    def wait_for_response(self, path, timeout=5):
        """Wait until response_received reports the local server path."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for response in network['responses']:
                if urlparse(response['url']).path == path:
                    return response
            time.sleep(0.1)
        return None

    def cancel_navigation(self):
        """Cancel load_url() in a second window and return how often the server saw the URL."""
        path = '/smoke/blocked-navigation'
        url = urljoin(self._window.real_url, path)
        second = webview.create_window(
            'Cancel navigation',
            html='<html><body>cancel navigation</body></html>',
            width=400,
            height=300,
        )

        def on_request(request):
            if request.url == url:
                return False

        second.events.request_sent += on_request
        closed = threading.Event()
        second.events.closed += closed.set
        try:
            if not second.events.loaded.wait(10):
                raise TimeoutError('Second window did not load')
            second.load_url(url)
            time.sleep(2)
        finally:
            second.destroy()
            closed.wait(5)

        return len(network['hits'].get(path, []))


def on_request(request):
    set_event('request_sent', request.__dict__)
    if urlparse(request.url).hostname not in ('127.0.0.1', 'localhost', '::1'):
        return

    network['requests'].append({'url': request.url, 'method': request.method})
    if urlparse(request.url).path == '/smoke/blocked':
        return False

    request.headers['X-Smoke'] = 'smoke'


def on_response(response):
    set_event('response_received', response.__dict__)
    if urlparse(response.url).hostname in ('127.0.0.1', 'localhost', '::1'):
        network['responses'].append({'url': response.url, 'status_code': response.status_code})


class Api:
    def eval(self, code):
        """Evaluate Python code in the context of this module. Errors propagate to JS."""
        return eval(code)

    def get_size(self):
        return self._window.width, self._window.height

    def get_window_info(self):
        w = self._window
        screens = webview.screens
        return {
            'title': w.title,
            'width': w.width,
            'height': w.height,
            'x': w.x,
            'y': w.y,
            'fullscreen': w.fullscreen,
            'on_top': w.on_top,
            'screens': [
                {'width': s.width, 'height': s.height, 'x': s.x, 'y': s.y} for s in screens
            ],
        }

    def evaluate_js(self, code):
        result = self._window.evaluate_js(code)
        return result

    def run_js(self, code):
        return self._window.run_js(code)

    def get_cookies(self):
        cookies = self._window.get_cookies()
        logger.debug(f'Cookies: {cookies}')
        return [cookie.output() for cookie in cookies]

    def clear_cookies(self):
        self._window.clear_cookies()

    def report(self, passed, failed, failures):
        """Print the test run summary to the terminal."""
        print(f'pywebview smoke test ({webview.renderer}): {passed} passed, {failed} failed')
        for failure in failures:
            print(f'  FAIL {failure}')

    async def asyncSleep(self, ms):
        await asyncio.sleep(ms / 1000)
        return ms

    _window = None
    _dom = None
    test1 = TestAPI()
    test2 = TestAPI()
    win = WindowAPI()
    dom = DomAPI()
    net = NetworkAPI()


def create_state(state):
    state.number = 0
    state.message = 'test'
    state.dict = {'key': 'value'}
    state.list = [1, 2, 3]
    state.nested = {
        'a': 1,
        'b': [1, 2, 3],
    }


events = {}


def set_event(name, value):
    events[name] = value


if __name__ == '__main__':
    api = Api()
    window = webview.create_window('pywebview', app, js_api=api, text_select=True)
    create_state(window.state)

    # Window events
    window.events.loaded += lambda: set_event('loaded', True)
    window.events.before_load += lambda: set_event('before_load', True)
    window.events.before_show += lambda: set_event('before_show', True)
    window.events.shown += lambda: set_event('shown', True)
    window.events.request_sent += on_request
    window.events.response_received += on_response

    api._window = window
    api._dom = window.dom
    api.win._window = window
    api.dom._window = window
    api.net._window = window
    window.expose(exposed_function)

    menu = [
        Menu(
            'Smoke test',
            [MenuAction('Re-run tests', lambda: window.run_js('location.reload()'))],
        )
    ]
    # ssl=True is intentionally omitted: python-for-android's cryptography recipe currently
    # fails to load on-device (dlopen cannot locate symbol "PyExc_TypeError" in the rust
    # extension), and the local server doesn't need HTTPS for this demo/test app.
    webview.start(private_mode=False, menu=menu)
