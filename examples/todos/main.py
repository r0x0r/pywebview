import webview

"""
An example of serverless app architecture
"""


class Api:
    def addItem(self, title):
        print(f'Added item {title}')

    def removeItem(self, item):
        print(f'Removed item {item}')

    def editItem(self, item):
        print(f'Edited item {item}')

    def toggleItem(self, item):
        print(f'Toggled item {item}')

    def toggleFullscreen(self):
        webview.windows[0].toggle_fullscreen()


if __name__ == '__main__':
    api = Api()
    webview.create_window('Todos magnificos', 'assets/index.html', js_api=api, min_size=(600, 450))
    webview.start(ssl=True)
