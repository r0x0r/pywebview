!function() {
  'use strict';
  window.pywebview._createApi(JSON.parse('%(functions)s')), 'qtwebengine' == window.pywebview.platform ? new QWebChannel(qt.webChannelTransport, function(channel) {
    window.pywebview._QWebChannel = channel, window.dispatchEvent(new CustomEvent('pywebviewready'));
  }) : window.dispatchEvent(new CustomEvent('pywebviewready'));
}();