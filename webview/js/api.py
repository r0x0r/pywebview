src = """
window.pywebview = {
    token: '%(token)s',
    platform: '%(platform)s',
    api: {},

    _createApi: function(funcList) {
        for(var i = 0; i < funcList.length; i++) {
            var element = funcList[i];
            var funcName = element.func;
            var params = element.params;

            // Create nested structure and assign function
            var funcHierarchy = funcName.split('.');
            var functionName = funcHierarchy.pop();
            var nestedObject = funcHierarchy.reduce(function (obj, prop) {
                if (!obj[prop]) {
                    obj[prop] = {};
                }
                return obj[prop];
            }, window.pywebview.api);

            // Define the function body
            var funcBody =
                'var __id = (Math.random() + "").substring(2);' +
                'var promise = new Promise(function(resolve, reject) {' +
                '    window.pywebview._checkValue("' + funcName + '", resolve, reject, __id);' +
                '});' +
                'window.pywebview._bridge.call("' + funcName + '", arguments, __id);' +
                'return promise;';

            // Assign the new function
            nestedObject[functionName] = new Function(params, funcBody);
            window.pywebview._returnValues[funcName] = {};
        };
    },

    _bridge: {
        call: function (funcName, params, id) {
            switch(window.pywebview.platform) {
                case 'mshtml':
                case 'cef':
                case 'qtwebkit':
                case 'android-webkit':
                    return window.external.call(funcName, pywebview._stringify(params), id);
                case 'chromium':
                    // Full file path support for WebView2
                    if (params.event instanceof Event && params.event.type === 'drop' && params.event.dataTransfer.files) {
                        chrome.webview.postMessageWithAdditionalObjects('FilesDropped', params.event.dataTransfer.files);
                    }
                    return window.chrome.webview.postMessage([funcName, pywebview._stringify(params), id]);
                case 'cocoa':
                case 'gtk':
                    return window.webkit.messageHandlers.jsBridge.postMessage(pywebview._stringify({funcName, params, id}));
                case 'qtwebengine':
                    if (!window.pywebview._QWebChannel) {
                        setTimeout(function() {
                            window.pywebview._QWebChannel.objects.external.call(funcName, pywebview._stringify(params), id);
                        }, 100)
                    } else {
                        window.pywebview._QWebChannel.objects.external.call(funcName, pywebview._stringify(params), id);
                    }
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
                    var pyError = JSON.parse(value);
                    var error = new Error(pyError.message);
                    error.name = pyError.name;
                    error.stack = pyError.stack;

                    reject(error);
                } else {
                    resolve(JSON.parse(value));
                }
            }
         }, 1)
    },
    _eventHandlers: {},
    _returnValues: {},
    _asyncCallback: function(result, id) {
        window.pywebview._bridge.call('pywebviewAsyncCallback', result, id)
    },
    _isPromise: function (obj) {
        return !!obj && (typeof obj === 'object' || typeof obj === 'function') && typeof obj.then === 'function';
    },

    _stringify: function stringify(obj) {
        function tryConvertToArray(obj) {
            try {
                return Array.prototype.slice.call(obj);
            } catch (e) {
                return obj;
            }
        }

        function isArrayLike(a) {
            return (
                a != null &&
                typeof(a[Symbol.iterator]) === 'function' &&
                typeof(a.length) === 'number' &&
                typeof(a) !== 'string'
            )
        }

        function serialize(obj, ancestors=[]) {
            try {
                if (obj instanceof Node) return pywebview.domJSON.toJSON(obj, { metadata: false, serialProperties: true });
                if (obj instanceof Window) return 'Window';

                var boundSerialize = serialize.bind(obj);

                if (typeof obj !== "object" || obj === null) {
                    return obj;
                }

                while (ancestors.length > 0 && ancestors[ancestors.length - 1] !== this) {
                    ancestors.pop();
                }

                if (ancestors.includes(obj)) {
                    return "[Circular Reference]";
                }
                ancestors.push(obj);

                if (isArrayLike(obj)) {
                    obj = tryConvertToArray(obj);
                }

                if (Array.isArray(obj)) {
                    const arr = obj.map(value => boundSerialize(value, ancestors));
                    return arr;
                }

                const newObj = {};
                for (const key in obj) {
                    if (typeof obj === 'function') {
                        continue;
                    }
                    newObj[key] = boundSerialize(obj[key], ancestors);
                }
                return newObj;

            } catch (e) {
                console.error(e)
                return e.toString();
            }
        }

      var _serialize = serialize.bind(null);

      return JSON.stringify(_serialize(obj));
  },

    _getNodeId: function (element) {
        if (!element) {
            return null;
        }
        var pywebviewId = element.getAttribute('data-pywebview-id') || Math.random().toString(36).substr(2, 11);
        if (!element.hasAttribute('data-pywebview-id')) {
            element.setAttribute('data-pywebview-id', pywebviewId);
        }
        return pywebviewId;
    },

    _insertNode: function (node, parent, mode) {
        if (mode === 'LAST_CHILD') {
            parent.appendChild(node);
        } else if (mode === 'FIRST_CHILD') {
            parent.insertBefore(node, parent.firstChild);
        } else if (mode === 'BEFORE') {
            parent.parentNode.insertBefore(node, parent);
        } else if (mode === 'AFTER') {
            parent.parentNode.insertBefore(node, parent.nextSibling);
        } else if (mode === 'REPLACE') {
            parent.parentNode.replaceChild(node, parent);
        }
    },

    _processElements: function (elements) {
        var serializedElements = [];

        for (var i = 0; i < elements.length; i++) {
            var pywebviewId;
            if (elements[i] === window) {
                pywebviewId = 'window';
            } else if (elements[i] === document) {
                pywebviewId = 'document';
            } else {
                pywebviewId = window.pywebview._getNodeId(elements[i]);
            }

            var node = pywebview.domJSON.toJSON(elements[i], {
                metadata: false,
                serialProperties: true,
                deep: false
            });

            node._pywebviewId = pywebviewId;
            serializedElements.push(node);
        }

        return serializedElements;
    },
}
window.pywebview._createApi(%(func_list)s);

if (window.pywebview.platform == 'qtwebengine') {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.pywebview._QWebChannel = channel;
        window.dispatchEvent(new CustomEvent('pywebviewready'));
    });
} else {
    window.dispatchEvent(new CustomEvent('pywebviewready'));
}
"""
