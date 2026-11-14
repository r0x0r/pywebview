import webview

if __name__ == '__main__':
    webview.settings['LOG_FORMAT'] = '%(asctime)s [%(name)s] %(levelname)-8s %(message)s'
    webview.create_window(
        'Custom log format', html='<h1>Check the console for timestamped logs</h1>'
    )
    webview.start(debug=True)
