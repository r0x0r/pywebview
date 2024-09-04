"""
    Custom alert box without the URL in the title bar for Windows
"""

src = """
window.alert = function(message) {
    var platform = '%(platform)s';

        if (platform == 'edgechromium') {
        window.chrome.webview.postMessage(['_pywebviewAlert', pywebview._stringify(message), 'alert']);    } else {
        window.external.alert(message);
    }

};

"""
