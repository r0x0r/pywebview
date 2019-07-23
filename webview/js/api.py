src = """
window.pywebview = {
    token: '%s',
    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            window.pywebview.api[funcList[i]] = (function (funcName) {
                return function(params) {
                    var promise = new Promise(function(resolve, reject) {
                        window.pywebview._checkValue(funcName, resolve);
                    });
                    window.pywebview._bridge.call(funcName, JSON.stringify(params));
                    return promise;
                }
            })(funcList[i])

            window.pywebview._returnValues[funcList[i]] = {
                isSet: false,
                value: undefined,
            }
        }
    },
    _bridge: {
        call: function (funcName, params) {
            switch(window.pywebview.platform) {
                case 'mshtml':
                case 'cef':
                case 'qtwebkit':
                    return window.external.call(funcName, params);
                case 'edgehtml':
                    return window.external.notify(JSON.stringify([funcName, params]));
                case 'cocoa':
                    return window.webkit.messageHandlers.jsBridge.postMessage(JSON.stringify([funcName, params]));
                case 'qtwebengine':
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        channel.objects.external.call(funcName, params);
                    });
                    break;
            }
        }
    },

    _checkValue: function(funcName, resolve) {
         var check = setInterval(function () {
            var returnObj = window.pywebview._returnValues[funcName];
            if (returnObj.isSet) {
                returnObj.isSet = false;
                try {
                    resolve(JSON.parse(returnObj.value));
                } catch(e) {
                    resolve(returnObj.value);
                }

                clearInterval(check);
            }
         }, 100)
    },
    platform: '%s',
    api: {},
    _returnValues: {}
}

window.pywebview._createApi(%s);
"""
