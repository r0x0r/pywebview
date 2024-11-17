window.pywebview._createApi(JSON.parse('%(functions)s'));

if (window.pywebview.platform == 'qtwebengine') {
  new QWebChannel(qt.webChannelTransport, function(channel) {
      window.pywebview._QWebChannel = channel;
      window.dispatchEvent(new CustomEvent('pywebviewready'));
  });
} else {
  window.dispatchEvent(new CustomEvent('pywebviewready'));
}

// return a magic value to indicate that the webview is ready
'%(LOADED_MAGIC_VALUE)s';
