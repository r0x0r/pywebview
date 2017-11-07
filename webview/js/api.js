window.pywebview = {
    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            window.pywebview.api[funcList[i]] = (function (func_name) {
                return function(params) {
                    return window.external.call(func_name, JSON.stringify(params))
                }
            })(funcList[i])
        }
    },
    api: {}
}

window.pywebview._createApi(%s)

