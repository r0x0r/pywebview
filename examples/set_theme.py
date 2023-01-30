import random
import sys
import threading
import time

import webview

"""
This example demonstrates how to change the theme of the webview window
"""

html = """
<!DOCTYPE html>
<html>
<body>


<button onClick="setTheme('light')">light theme</button><br/>
<button onClick="setTheme('dark')">dark theme</button><br/>
<button onClick="setTheme('system')">system</button><br/>

<script>
    function setTheme(theme) {
        pywebview.api.set_theme(theme)
    }


</script>
</body>
</html>
"""


class Api:
    def set_theme(self,theme):
        active_window = webview.active_window()
        if active_window:
            active_window.set_theme(theme)


if __name__ == '__main__':
    api = Api()
    window = webview.create_window('API example',  html=html, js_api=api, transparent=True,vibrancy=True)
    webview.start()
