"""Async JS API functions and event handlers running on an asyncio event loop."""

import asyncio

import webview

html = """
<!DOCTYPE html>
<html>
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
    await asyncio.sleep(0.1)
    print(f'Page loaded: {window.get_current_url()}')


if __name__ == '__main__':
    window = webview.create_window('Async API example', html=html, js_api=Api())
    window.events.loaded += on_loaded

    # An event loop is started automatically for async functions. To use your own loop,
    # pass it with webview.start(event_loop=loop).
    webview.start()
