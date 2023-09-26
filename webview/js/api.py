src = """
window.pywebview = {
    token: '%(token)s',
    platform: '%(platform)s',
    api: {},

    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            var funcName = funcList[i].func;
            var params = funcList[i].params;

            var funcBody =
                "var __id = (Math.random() + '').substring(2); " +
                "var promise = new Promise(function(resolve, reject) { " +
                    "window.pywebview._checkValue('" + funcName + "', resolve, reject, __id); " +
                "}); " +
                "window.pywebview._bridge.call('" + funcName + "', arguments, __id); " +
                "return promise;"

            window.pywebview.api[funcName] = new Function(params, funcBody)
            window.pywebview._returnValues[funcName] = {}
        }
    },

    _bridge: {
        call: function (funcName, params, id) {
            switch(window.pywebview.platform) {
                case 'mshtml':
                case 'cef':
                case 'qtwebkit':
                    return window.external.call(funcName, JSON.stringify(params), id);
                case 'chromium':
                    return window.chrome.webview.postMessage([funcName, pywebview._stringify(params), id]);
                case 'cocoa':
                case 'gtk':
                    return window.webkit.messageHandlers.jsBridge.postMessage(JSON.stringify([funcName, params, id]));
                case 'qtwebengine':
                    if (!window.pywebview._QWebChannel) {
                        setTimeout(function() {
                            window.pywebview._QWebChannel.objects.external.call(funcName, JSON.stringify(params), id);
                        }, 100)
                    } else {
                        window.pywebview._QWebChannel.objects.external.call(funcName, JSON.stringify(params), id);
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
        function serialize(obj, depth=0, visited=new WeakSet()) {
            try {
                if (obj instanceof Node) return pywebview.domJSON.toJSON(obj, { metadata: false, serialProperties: true });
                if (obj instanceof Window) return 'Window';
                if (typeof obj === 'function') return 'function';

                if (visited.has(obj)) {
                    return '[Circular Reference]';
                }

                if (typeof obj === 'object' && obj !== null) {
                    visited.add(obj);

                    if (Array.isArray(obj)) {
                        const arr = obj.map(value => serialize(value, depth + 1, visited));
                        visited.delete(obj);
                        return arr;
                    }

                    const newObj = {};
                    for (const key in obj) {
                        newObj[key] = serialize(obj[key], depth + 1, visited);
                    }
                    visited.delete(obj);
                    return newObj;
                }

                return obj;
            } catch (e) {
                console.error(e)
                return e.toString();
            }
        }

        return JSON.stringify(serialize(obj));
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
            var pywebviewId = window.pywebview._getNodeId(elements[i]);
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
