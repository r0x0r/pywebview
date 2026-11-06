"""Demonstrates edge snapping for a frameless window (``SNAP_ON_DRAG``).

A frameless window loses the system's edge snapping on Windows: the caption is gone, and the web
content is hosted in a child window that answers ``WM_NCHITTEST`` with ``HTCLIENT`` everywhere, so
the OS never treats a drag as a caption drag. With ``webview.settings['SNAP_ON_DRAG'] = True`` the
page keeps track of the drag instead and, when the window is released near a screen edge, it is
snapped to half or a quarter of the work area.

Drag the dark bar to the left or right screen edge and release: the window snaps to that half.
Drag it to a corner: it snaps to a quarter. Dragging anywhere else just moves the window.

Note: with snapping enabled the drag is handled in JavaScript rather than by the native move loop,
because the page has to see the mouse-up that decides where to snap.
"""

import webview

html = """
<!DOCTYPE html>
<html>
<head>
    <style type="text/css">
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            background-color: #f5f5f5;
            color: #222;
        }

        .pywebview-drag-region {
            background: #2b3245;
            color: white;
            padding: 14px 18px;
            cursor: move;
            font-weight: bold;
            user-select: none;
        }

        .content {
            padding: 20px;
        }

        code {
            background: #e8e8e8;
            padding: 2px 5px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="pywebview-drag-region">Drag this bar to a screen edge and release</div>

    <div class="content">
        <p>The window snaps to:</p>
        <ul>
            <li>left / right edge &rarr; that half of the work area</li>
            <li>top edge &rarr; the whole work area (maximized)</li>
            <li>a corner &rarr; that quarter</li>
        </ul>
        <p>Snapping is on while <code>webview.settings['SNAP_ON_DRAG']</code> is <code>True</code>;
           the trigger distance is <code>webview.settings['SNAP_TRIGGER']</code> pixels.</p>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    webview.settings['SNAP_ON_DRAG'] = True

    webview.create_window(
        'Frameless snap example',
        html=html,
        frameless=True,
        easy_drag=False,
        width=1024,
        height=640,
    )
    webview.start()
