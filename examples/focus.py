import webview

"""
Create a non-focusable window that can be useful for onscreen floating tools.
"""

if __name__ == '__main__':
    webview.create_window('Nonfocusable window', html='<html><head></head><body><p>You shouldnt be able to type into this window...</p><input type="text"><p>...but still you can click elements in this window...</p><input type="checkbox"></body></html>', focus=False)
    webview.start()
