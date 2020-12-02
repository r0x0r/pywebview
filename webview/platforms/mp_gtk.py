import multiprocessing as mp
from webview import Window
from webview.platforms import gtk as guilib
from uuid import uuid4
from threading import Thread

queue = mp.Queue()
event_queue = mp.Queue()
windows = {}
return_dict = {}

logger = guilib.logger
webkit_ver = guilib.webkit_ver
old_webkit = guilib.old_webkit
renderer = guilib.renderer
settings = guilib.settings


def _create_window(*args):
    window = Window(*args)
    window._initialize(guilib, False, True)
    window.closed += lambda: event_queue.put((args[0], 'closed'))
    window.closing += lambda: event_queue.put((args[0], 'closing'))
    window.loaded += lambda: event_queue.put((args[0], 'loaded'))
    window.shown += lambda: event_queue.put((args[0], 'shown'))
    guilib.create_window(window)


def proc_func():
    def data_loop():
        while 1:
            data = queue.get()
            func = _create_window if data[0] == 'create_window' else getattr(
                guilib, data[0])
            r = func(*data[2:])
            if data[1]:
                return_dict[data[1]] = r

    data = queue.get()
    t = Thread(target=data_loop)
    t.daemon = True
    t.start()
    _create_window(*data[2:])


p = mp.Process(target=proc_func)
p.start()


def event_loop():
    uid, event = event_queue.get()
    getattr(windows[uid], event).set()


event_thread = Thread(target=event_loop)
event_thread.daemon = True
event_thread.start()


def create_window(window):
    windows[window.uid] = window
    queue.put(
        ('create_window', None, window.uid, window.title, window.real_url,
         window.html, window.initial_width, window.initial_height,
         window.initial_x, window.initial_y, window.resizable,
         window.fullscreen, window.min_size, window.hidden, window.frameless,
         window.easy_drag, window.minimized, window.on_top,
         window.confirm_close, window.background_color, window._js_api,
         window.text_select, window.transparent))


def set_title(title, uid):
    queue.put(('set_title', None, title, uid))


def destroy_window(uid):
    queue.put(('destroy_window', None, uid))


def toggle_fullscreen(uid):
    queue.put(('toggle_fullscreen', None, uid))


def set_on_top(uid, top):
    queue.put(('set_on_top', None, uid, top))


def resize(width, height, uid):
    queue.put(('resize', None, width, height, uid))


def move(x, y, uid):
    queue.put(('move', None, x, y, uid))


def hide(uid):
    queue.put(('hide', None, uid))


def show(uid):
    queue.put(('show', None, uid))


def minimize(uid):
    queue.put(('minimize', None, uid))


def restore(uid):
    queue.put(('restore', None, uid))


def get_current_url(uid):
    id = uuid4().hex[:8]
    queue.put(('get_current_url', id, uid))
    while not id in return_dict:
        pass
    return return_dict[id]


def load_url(url, uid):
    queue.put(('load_url', None, url, uid))


def load_html(content, base_uri, uid):
    queue.put(('load_html', None, content, base_uri, uid))


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename,
                       file_types, uid):
    id = uuid4().hex[:8]
    queue.put(('create_file_dialog', id, dialog_type, directory,
               allow_multiple, save_filename, file_types, uid))
    while not id in return_dict:
        pass
    return return_dict[id]


def evaluate_js(script, uid):
    id = uuid4().hex[:8]
    queue.put(('evaluate_js', id, script, uid))
    while not id in return_dict:
        pass
    return return_dict[id]


def get_position(uid):
    id = uuid4().hex[:8]
    queue.put(('get_position', id, uid))
    while not id in return_dict:
        pass
    return return_dict[id]


def get_size(uid):
    id = uuid4().hex[:8]
    queue.put(('get_size', id, uid))
    while not id in return_dict:
        pass
    return return_dict[id]
