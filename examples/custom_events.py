"""Subscribe and unsubscribe custom pywebview events."""

import webview

html_content = """<html><body><h1>Custom Events Test</h1></body></html>"""

def on_custom_event(data=None):
    print(f"Custom event triggered, data: {data}")

def on_another_event():
    print("Another custom event triggered without data")

def on_closed():
    print('pywebview window is closed')

def on_load(window):
    print("1. Triggering custom_event (should show both listeners):")
    window.events.custom_event("Hello from the custom event!")

    print("2. Removing listener from another_event")
    window.events.another_event -= on_another_event

    print("3. Triggering another_event after removing listener (should be silent):")
    window.events.another_event()

    print("4. Adding listener back and triggering again:")
    window.events.another_event += on_another_event
    window.events.another_event()

    print("5. Force the closed event to be triggered (this should not close the window, just trigger the event):")
    window.events.closed()

if __name__ == '__main__':
    window = webview.create_window(
        'Custom Events Test',
        html=html_content
    )

    window.events.custom_event += on_custom_event
    window.events.another_event += on_another_event
    window.events.closed += on_closed

    webview.start(on_load, window)