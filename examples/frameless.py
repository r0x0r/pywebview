"""Create a frameless window with a custom title bar.

The title bar is hidden. The page resize handles come as part of a frameless
window; KEEP_FRAME_STYLES additionally keeps the native frame styles, which is
what restores snapping and a work-area-aware maximize. Windows only
(WinForms / EdgeChromium).
"""

import webview

webview.settings['KEEP_FRAME_STYLES'] = True

HTML = """<html>
<head>
<style>
    html, body { height: 100%; margin: 0; font-family: 'Segoe UI', sans-serif; }
    .titlebar {
        display: flex; justify-content: space-between; align-items: center;
        height: 40px; box-sizing: border-box; background: #2b5797; color: white;
    }
    .title { flex: 1; padding: 0 12px; line-height: 40px; user-select: none; }
    button { border: 0; background: transparent; color: white; font: inherit;
             height: 40px; width: 44px; cursor: pointer; }
    button:hover { background: #3c6eb5; }
    .content { padding: 16px 24px; }
    li { margin-bottom: 6px; }
</style>
</head>
<body>
    <div class="titlebar">
        <span class="title pywebview-drag-region">Frameless window</span>
        <span>
            <button onclick="pywebview.api.minimize()">&#8722;</button>
            <button onclick="pywebview.api.maximize()">&#9633;</button>
            <button onclick="pywebview.api.restore()">&#10697;</button>
            <button onclick="pywebview.api.close()">&#10005;</button>
        </span>
    </div>
    <div class="content">
        <p>Try it out:</p>
        <ul>
            <li>Drag any edge or corner to resize. The cursor changes on its own.</li>
            <li>Drag the blue title to the left, right or top of the screen to snap.</li>
            <li>Drag a snapped window away, or press <em>restore</em> above.</li>
            <li>Press <em>maximize</em>: the page stops at the taskbar, corners stay round.</li>
        </ul>
    </div>
</body>
</html>
"""


class Api:
    def __init__(self):
        self.window = None

    def minimize(self):
        self.window.minimize()

    def maximize(self):
        self.window.maximize()

    def restore(self):
        self.window.restore()

    def close(self):
        self.window.destroy()


if __name__ == '__main__':
    api = Api()
    api.window = webview.create_window(
        'Frameless window', html=HTML, frameless=True, easy_drag=False, js_api=api
    )
    webview.start()
