window.pywebview = {
    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            window.pywebview.api[funcList[i]] = (function (funcName) {
                return function(params) {
                    var promise = new Promise(function(resolve, reject) {
                        window.pywebview._checkValue(funcName, resolve);
                    });
                    window.pywebview._bridge.call(funcName, JSON.stringify(params))

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
        call: function (func_name, params) {
            if (window.external) {
                return window.external.call(func_name, params)
            } else if (window.qt) {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                  channel.objects.external.call(func_name, params)
                });
            }
        }
    },

    _checkValue: function(funcName, resolve) {
         var check = setInterval(function () {
            var returnObj = window.pywebview._returnValues[funcName]

            if (returnObj.isSet) {
                returnObj.isSet = false
                try {
                    resolve(JSON.parse(returnObj.value.replace(/\n/, '\\n')))
                } catch(e) {
                    resolve(returnObj.value)
                }

                clearInterval(check);
            }
         }, 100)
    },
    api: {},
    _returnValues: {},

}

window.pywebview._createApi(%s)
