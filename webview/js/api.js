window.pywebview = {
    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            window.pywebview.api[funcList[i]] = (function (funcName) {
                return function(params) {
                    var promise = new Promise(function(resolve, reject){
                        function checkValue(funcName) {
                            setTimeout(function() {
                                var returnObj = window.pywebview._returnValues[funcName]

                                if (returnObj.isSet) {
                                    returnObj.isSet = false;
                                    resolve(returnObj.value);
                                } else {
                                    checkValue(funcName)
                                }
                            }, 200);
                        }
                        checkValue(funcName);
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
        call: function(func_name, params) {
            if (window.external) {
                return window.external.call(func_name, params)
            }
        }
    },
    api: {},
    _returnValues: {}
}

window.pywebview._createApi(%s)

