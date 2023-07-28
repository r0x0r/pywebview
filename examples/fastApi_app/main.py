from app import app
import subprocess
import uvicorn
import asyncio
import webview
import os

"""
An example of serverless app architecture
"""

class Api:

    # Your method`s

    pass

async def web():
    api = Api()
    window = webview.create_window(
        'Todos magnificos',
        url='http://127.0.0.1:8000',
        js_api=api,
        frameless=True,
        min_size=(1250, 750)
    )
    webview.start(debug=True)

async def start():
    server_process = subprocess.Popen(["uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"])

    # Give some time for the server to start before launching the webview
    await asyncio.sleep(2)

    # Terminate the server process after closing the webview
    server_process.terminate()

if __name__ == '__main__':

    asyncio.run(start())
