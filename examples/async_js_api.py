"""Expose async Python methods using one application-owned asyncio event loop."""

import asyncio
import threading

import webview

html = r"""
<html>
<body>
    <button onclick="load()">Run two concurrent async calls</button>
    <pre id="result"></pre>
    <script>
        async function load() {
            const output = document.getElementById('result')
            output.textContent = 'Waiting...'
            try {
                const values = await Promise.all([
                    window.pywebview.api.greet('Alice'),
                    window.pywebview.api.greet('Bob')
                ])
                output.textContent = values.join('\n')
            } catch (error) {
                output.textContent = error.message
            }
        }
    </script>
</body>
</html>
"""


class Api:
    async def greet(self, name):
        await asyncio.sleep(1)
        return f'Hello, {name}!'


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    ready = threading.Event()

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.call_soon(ready.set)
        loop.run_forever()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()

    thread = threading.Thread(target=run_loop, name='asyncio-loop')
    thread.start()
    ready.wait()
    try:
        webview.create_window('Async JS API', html=html, js_api=Api())
        webview.start(event_loop=loop)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
