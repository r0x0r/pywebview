"""Frameless window that keeps the system's keyboard window management.

``frameless=True`` strips ``WS_CAPTION``/``WS_THICKFRAME``, and the system then stops managing the
window: on Windows ``Win``+``Left``/``Right`` do nothing, and ``Win``+``Up`` maximizes to the whole
screen instead of the work area, so the taskbar is covered.

With ``webview.settings['KEEP_FRAME_STYLES'] = True`` pywebview re-adds those styles and hides the
frame by collapsing the non-client area to zero size, so nothing is drawn but the window is a normal
window again as far as the system is concerned:

* ``Win``+``Left``/``Right`` snap to the halves of the work area
* ``Win``+``Up`` maximizes to the work area exactly (``WM_GETMINMAXINFO`` is handled for you)
* ``Win``+``Down`` restores
* ``Alt``+``Space`` opens the system menu

The client rectangle still equals the window rectangle, so a frameless window keeps looking frameless
and page coordinates are unaffected.

Mouse resizing is not part of this: the web content sits in a child window that answers the hit test
for the whole client area, so the top-level window never learns where the cursor is. Implement resize
handles in the page (see the Drag area section of the docs) if you need them.

Press the key combinations while this example is running to see the window follow along.
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
            background: #f5f5f5;
            color: #222;
        }

        .pywebview-drag-region {
            background: #2b3245;
            color: white;
            padding: 14px 18px;
            cursor: move;
            font-weight: bold;
        }

        .content {
            padding: 20px;
        }

        kbd {
            border: 1px solid #bbb;
            border-bottom-width: 2px;
            border-radius: 4px;
            padding: 1px 6px;
            background: #fff;
        }
    </style>
</head>
<body>
    <div class="pywebview-drag-region">Frameless, but the system still manages it</div>

    <div class="content">
        <p>Try:</p>
        <ul>
            <li><kbd>Win</kbd> + <kbd>&larr;</kbd> / <kbd>&rarr;</kbd> - snap to that half</li>
            <li><kbd>Win</kbd> + <kbd>&uarr;</kbd> - maximize to the work area (not over the taskbar)</li>
            <li><kbd>Win</kbd> + <kbd>&darr;</kbd> - restore</li>
            <li><kbd>Alt</kbd> + <kbd>Space</kbd> - system menu</li>
        </ul>
        <p>This is off by default; enable it with
           <code>webview.settings['KEEP_FRAME_STYLES'] = True</code>.</p>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    webview.settings['KEEP_FRAME_STYLES'] = True

    webview.create_window(
        'Frameless window with frame styles',
        html=html,
        frameless=True,
        easy_drag=False,
        width=1024,
        height=640,
    )
    webview.start()
