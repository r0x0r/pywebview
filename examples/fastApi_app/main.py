from app import app
import uvicorn
import asyncio
import webview
import os

"""
An example of FastAPI app architecture
"""

async def server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

async def web():

    window = webview.create_window(
        'Todos magnificos',
        url='http://127.0.0.1:8000',
        # js_api=api,
        frameless=True,
        min_size=(1250, 750)
    )
    webview.start(debug=True)

async def start():
    await asyncio.gather(web(), server())

if __name__ == '__main__':
    asyncio.run(start())
