""" Dispatch customs events in js:
        window.addEventListener("personalEvent", (e) => {
            console.log("Received from Python:", e.customvalue);
        });
"""

import webview

html_content = """<html><body><script>
    window.addEventListener("personalEvent", (e) => {
        // Displays e.customvalue in screen
        var h1 = document.createElement('h1')
        var text = document.createTextNode(e.customvalue)
        h1.appendChild(text)
        document.body.appendChild(h1)
        // Use e.preventDefault()
        if (e.customvalue == "123") {e.preventDefault()};
    });
</script></body></html>"""

def dispatch_custom_event(window):
    result1 = window.dispatch_custom_event('personalEvent', {'customvalue': True})
    if (result1): print("No listener called e.preventDefault()")
    
    result2 = window.dispatch_custom_event('personalEvent', {'customvalue': "123"})
    if (not result2): print("Some listener called e.preventDefault()")


if __name__ == '__main__':
    window = webview.create_window('Dispatch customs events', html=html_content)
    webview.start(dispatch_custom_event, window)