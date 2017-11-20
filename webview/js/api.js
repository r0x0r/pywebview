window.pywebview = {
    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            window.pywebview.api[funcList[i]] = (function (func_name) {
                return function(params) {
                    return window.pywebview._bridge.call(func_name, JSON.stringify(params))
                }
            })(funcList[i])
        }
    },
    _bridge: {
        call: function(func_name, params) {
            if (window.external) {
                return window.external.call(func_name, params)
            }
        }
    },
    api: {}
}

window.pywebview._createApi(%s)

