"""Async JS API functions and event handlers running on an asyncio event loop."""

import asyncio

import webview

html = """
<!DOCTYPE html>
<html>
<head>
  <title>Async API example</title>
</head>
<body>
  <button onclick="fetchData()">Fetch data</button>
  <div id="result"></div>
  <script>
    function fetchData() {
      document.getElementById('result').innerText = 'Loading...'
      pywebview.api.fetch_data(1).then(function(response) {
        document.getElementById('result').innerText = response.message
      })
    }
  </script>
</body>
</html>
"""


class Api:
    async def fetch_data(self, delay):
        await asyncio.sleep(delay)
        return {'message': f'Data fetched after {delay} second(s)'}


async def on_loaded(window):
    # Window methods are synchronous. Run them in a thread so the event loop is not blocked.
    title = await asyncio.to_thread(window.evaluate_js, 'document.title')
    print(f'Page loaded: {title}')


async def on_closing():
    await asyncio.sleep(0.1)
    return True


if __name__ == '__main__':
    window = webview.create_window('Async API example', html=html, js_api=Api())

    # loaded is a non-blocking event, so its handler can be async
    window.events.loaded += on_loaded

    # closing is a blocking event: pywebview waits for its handlers and uses their return
    # value, so they must be regular functions. Subscribing an async handler raises TypeError.
    try:
        window.events.closing += on_closing
    except TypeError as e:
        print(e)

    # An event loop is started automatically for async functions. To use your own loop,
    # pass it with webview.start(event_loop=loop).
    webview.start()
