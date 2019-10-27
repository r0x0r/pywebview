src = """
window.pywebview = {
    token: '%s',
    platform: '%s',
    api: {},
    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            window.pywebview.api[funcList[i]] = (function (funcName) {
                return function(params) {
                    var id = (Math.random() + '').substring(2)
                    var promise = new Promise(function(resolve, reject) {
                        window.pywebview._checkValue(funcName, resolve, reject, id);
                    });

                    window.pywebview._bridge.call(funcName, JSON.stringify(params), id);
                    return promise;
                }
            })(funcList[i])

            window.pywebview._returnValues[funcList[i]] = {}
        }
    },
    _bridge: {
        call: function (funcName, params, id) {
            switch(window.pywebview.platform) {
                case 'mshtml':
                case 'cef':
                case 'qtwebkit':
                    return window.external.call(funcName, params, id);
                case 'edgehtml':
                    return window.external.notify(JSON.stringify([funcName, params, id]));
                case 'cocoa':
                    return window.webkit.messageHandlers.jsBridge.postMessage(JSON.stringify([funcName, params, id]));
                case 'qtwebengine':
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        channel.objects.external.call(funcName, params, id);
                    });
                    break;
            }
        }
    },

    _checkValue: function(funcName, resolve, reject, id) {
         var check = setInterval(function () {
            var returnObj = window.pywebview._returnValues[funcName][id];
            if (returnObj) {
                var value = returnObj.value;
                var isError = returnObj.isError;

                delete window.pywebview._returnValues[funcName][id];
                clearInterval(check);

                if (isError) {
                    reject(new Error(value));
                } else {
                    resolve(JSON.parse(value));
                }
            }
         }, 100)
    },
    _returnValues: {},
    _events: {
        pywebviewready: new Event('pywebviewready')
    }
}
window.pywebview._createApi(%s);
document.dispatchEvent(pywebview._events.pywebviewready);
"""
