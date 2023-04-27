import webview

if __name__ == "__main__":
    webview.create_window("Local SSL Test", "assets/index.html")
    gui = None
    webview.start(gui=gui, ssl=True)
