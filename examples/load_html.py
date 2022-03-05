import webview


class Api:
    def write(self, *args):
        print(''.join(args))

html = """
<body>
<input type="text" value="bla"></input>
<input id="haha" type="text" value="blubb"></input>
</body>
<script type="text/javascript">

window.addEventListener('focus', function(event) {
    pywebview.api.write(`FOCUSIN ${event.target.value} ${document.hasFocus()}`)
})
window.addEventListener('focusout', function(event) {
    pywebview.api.write(`FOCUSOUT ${event.target.value} ${document.hasFocus()}`)
})
</script>"""

window = webview.create_window('b', js_api=Api(), html=html, width=200, height=200)

webview.start()