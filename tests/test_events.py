import os
import time

import webview

from .util import run_test

LIFECYCLE_EVENTS = ('before_load', 'loaded', 'before_show', 'shown')


def test_lifecycle_events():
    window = webview.create_window('Events test', html='<html><body>TEST</body></html>')
    fired = []

    for name in LIFECYCLE_EVENTS:
        # Bound as a default argument: the handler is called with no arguments,
        # and a closure over the loop variable would record the last name.
        event = getattr(window.events, name)
        event += lambda name=name: fired.append(name)

    run_test(webview, window, lifecycle_test, (fired,))


def lifecycle_test(window, fired):
    # Ordering between the show and load pairs is not guaranteed, only within
    # each pair.
    for _ in range(50):
        if all(name in fired for name in LIFECYCLE_EVENTS):
            break
        time.sleep(0.1)

    missing = [name for name in LIFECYCLE_EVENTS if name not in fired]
    assert not missing, f'events did not fire: {missing} (fired: {fired})'
    assert fired.index('before_load') < fired.index('loaded'), fired
    assert fired.index('before_show') < fired.index('shown'), fired


def test_app_events(monkeypatch, tmp_path):
    opened = tmp_path / 'document.txt'
    opened.write_text('test')
    argv = [str(opened), 'myapp://open?id=1', '--not-a-file', 'key:value']
    monkeypatch.setattr('sys.argv', ['app', *argv])

    window = webview.create_window('App events test', html='<html><body>TEST</body></html>')
    fired = []
    webview.events.started += lambda: fired.append('started')
    webview.events.opened += lambda request: fired.append(request)

    run_test(webview, window, app_events, (fired, argv, str(opened)))


def app_events(window, fired, argv, path):
    for _ in range(50):
        if len(fired) == 2:
            break
        time.sleep(0.1)

    # Handlers run in their own threads, so only the firing order is guaranteed, not this one
    assert 'started' in fired, fired
    assert {'files': [path], 'urls': ['myapp://open?id=1'], 'argv': argv, 'cwd': os.getcwd()} in (
        fired
    ), fired


def test_quitting():
    window = webview.create_window('Quitting test')
    quitting = []

    def on_quitting():
        quitting.append(True)
        return len(quitting) > 1

    webview.events.quitting += on_quitting

    # Closing the last window fires quitting, which can cancel it
    assert window._fire_quitting()
    assert not window._fire_quitting()

    # Closing a window while another one is open does not quit
    webview.create_window('Second window')
    assert not window._fire_quitting()
    assert len(quitting) == 2


def test_quitting_on_destroy():
    window = webview.create_window(
        'Quitting on destroy test', html='<html><body>TEST</body></html>'
    )
    quitting = []
    webview.events.quitting += lambda: quitting.append(True)

    # run_test closes the last window with window.destroy()
    run_test(webview, window)
    assert quitting == [True], quitting
