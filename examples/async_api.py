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


async def async_on_closing():
    return True


can_close = False


def on_closing():
    # closing cannot have an async handler. To run async code before the window closes,
    # cancel closing, run the coroutine on the event loop and close the window when it is done.
    if can_close:
        return True

    asyncio.run_coroutine_threadsafe(save_and_close(), loop)
    return False  # keep the window open for now


async def save_and_close():
    global can_close
    await asyncio.sleep(1)  # e.g. save data
    print('Data saved')
    # Some backends fire closing again on window.destroy(), so let the second close through
    can_close = True
    window.destroy()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    window = webview.create_window('Async API example', html=html, js_api=Api())

    # loaded is a non-blocking event, so its handler can be async
    window.events.loaded += on_loaded

    # closing is a blocking event: pywebview waits for its handlers and uses their return
    # value, so they must be regular functions. Subscribing an async handler raises TypeError.
    try:
        window.events.closing += async_on_closing
    except TypeError as e:
        print(e)

    window.events.closing += on_closing

    # Without event_loop, pywebview starts its own loop for async functions. A loop is passed
    # here so that on_closing can schedule a coroutine on it.
    webview.start(event_loop=loop)
