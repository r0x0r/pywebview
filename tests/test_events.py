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
