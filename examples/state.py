import webview

html = """
<!DOCTYPE html>
<html>
    <head>
       <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
    </head>

    <script>
        window.addEventListener('pywebviewready', () => {
            window.pywebview.state.addEventListener('change', event => {
                console.log('Counter value changed:', event)
                document.getElementById('counter').innerText = pywebview.state.counter
            })
        })

        function increaseCounter() {
            pywebview.state.counter++
            document.getElementById('counter').innerText = pywebview.state.counter
        }
    </script>

    <body>
        <h1>State</h1>

        <p>Counter value: <span id="counter">0</span></p>

        <button onclick="increaseCounter()">Increase counter from JS</button>
        <button onclick="pywebview.api.decrease_counter()">Decrease counter from Python</button>
    </body>
</html>
"""

def on_counter_change(type, key, value):
    print(f'Event {type} for {key} value : {value}')

def decrease_counter():
    window.state.counter -= 1

def on_loaded(window):
    window.expose(decrease_counter)
    window.state += on_counter_change

if __name__ == '__main__':
    global window
    window = webview.create_window('State example', html=html)
    window.state.counter = 0
    window.events.loaded += on_loaded
    webview.start(debug=True)