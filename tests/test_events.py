import time

import webview

from .util import run_test

LIFECYCLE_EVENTS = ('before_load', 'loaded', 'before_show', 'shown')


def test_lifecycle_events():
    window = webview.create_window('Events test', html='<html><body>TEST</body></html>')
    fired = []

    for name in LIFECYCLE_EVENTS:
        # The name is bound as a default argument because the handler is called
        # with no arguments, and a closure over the loop variable would record
        # the last name four times.
        event = getattr(window.events, name)
        event += lambda name=name: fired.append(name)

    run_test(webview, window, lifecycle_test, (fired,))


def lifecycle_test(window, fired):
    # before_show and shown fire around window creation and loaded around
    # navigation, so ordering between the two pairs is not guaranteed - but each
    # pair is ordered, and by now all four should have been dispatched.
    for _ in range(50):
        if all(name in fired for name in LIFECYCLE_EVENTS):
            break
        time.sleep(0.1)

    missing = [name for name in LIFECYCLE_EVENTS if name not in fired]
    assert not missing, f'events did not fire: {missing} (fired: {fired})'
    assert fired.index('before_load') < fired.index('loaded'), fired
    assert fired.index('before_show') < fired.index('shown'), fired
