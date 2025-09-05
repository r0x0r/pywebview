
export function initPywebview() {

  window.pywebview = {
    token: '%(token)s',
    platform: '%(platform)s',
    api: {},
    _eventHandlers: {},
    _returnValuesCallbacks: {},

    _createApi(funcList) {
      const sanitize_params = (params) => {
        const reservedWords = [
          'case',
          'catch',
          'const',
          'debugger',
          'default',
          'delete',
          'do',
          'export',
          'extends',
          'false',
          'function',
          'instanceof',
          'let',
          'new',
          'null',
          'super',
          'switch',
          'this',
          'throw',
          'true',
          'typeof',
          'var',
          'void',
        ];

        for (let i = 0; i < params.length; i++) {
          const param = params[i];
          if (reservedWords.includes(param)) {
            params[i] = param + '_';
          }
        }

        return params;
      };

      for (const element of funcList) {
        const funcName = element.func;
        const params = element.params;

        // Create nested structure and assign function
        const funcHierarchy = funcName.split('.');
        const functionName = funcHierarchy.pop();
        const nestedObject = funcHierarchy.reduce((obj, prop) => {
          if (!obj[prop]) {
            obj[prop] = {};
          }
          return obj[prop];
        }, window.pywebview.api);

        // Define the function body
        const funcBody = `var __id = (Math.random() + "").substring(2);
          var promise = new Promise(function(resolve, reject) {
              window.pywebview._checkValue("${funcName}", resolve, reject, __id);
          });
          window.pywebview._jsApiCallback("${funcName}", Array.prototype.slice.call(arguments), __id);
          return promise;`;

        // Assign the new function
        nestedObject[functionName] = new Function(
          sanitize_params(params),
          funcBody
        );
        window.pywebview._returnValuesCallbacks[funcName] = {};
      }
    },

    _jsApiCallback(funcName, params, id) {
      switch (window.pywebview.platform) {
        case 'mshtml':
        case 'cef':
        case 'qtwebkit':
        case 'android-webkit':
          return window.external.call(funcName, pywebview.stringify(params), id);
        case 'edgechromium':
          // Full file path support for WebView2
          if (
            params.event instanceof Event &&
            params.event.type === 'drop' &&
            params.event.dataTransfer.files
          ) {
            chrome.webview.postMessageWithAdditionalObjects(
              'FilesDropped',
              params.event.dataTransfer.files
            );
          }
          return window.chrome.webview.postMessage([
            funcName,
            pywebview.stringify(params),
            id,
          ]);
        case 'cocoa':
        case 'gtkwebkit2':
          return window.webkit.messageHandlers.jsBridge.postMessage(
            pywebview.stringify(
              { funcName, params, id }
            )
          );
        case 'qtwebengine':
          if (!window.pywebview._QWebChannel) {
            setTimeout(() => {
              window.pywebview._QWebChannel.objects.external.call(
                funcName,
                pywebview.stringify(params),
                id
              );
            }, 100);
          } else {
            window.pywebview._QWebChannel.objects.external.call(
              funcName,
              pywebview.stringify(params),
              id
            );
          }
          break;
        default:
          break;
      }
    },

    _checkValue(funcName, resolve, reject, id) {
      window.pywebview._returnValuesCallbacks[funcName][id] = (returnObj) => {
        const { value, isError } = returnObj;

        delete window.pywebview._returnValuesCallbacks[funcName][id];

        if (isError) {
          const pyError = JSON.parse(value);
          const error = new Error(pyError.message);
          error.name = pyError.name;
          error.stack = pyError.stack;

          reject(error);
        } else {
          resolve(JSON.parse(value));
        }
      };
    },
    _asyncCallback(result, id) {
      window.pywebview._jsApiCallback('pywebviewAsyncCallback', result, id);
    },
    _isPromise(obj) {
      return (
        !!obj &&
        (typeof obj === 'object' || typeof obj === 'function') &&
        typeof obj.then === 'function'
      );
    },

    stringify(obj, timing) {
      const tryConvertToArray = (obj) => {
        try {
          return Array.prototype.slice.call(obj);
        } catch (e) {
          return obj;
        }
      };

      const isArrayLike = (a) => {
        return (
          a &&
          typeof a[Symbol.iterator] === 'function' &&
          typeof a.length === 'number' &&
          typeof a !== 'string'
        );
      };

      const serialize = (obj, ancestors) => {
        try {
          if (obj instanceof Node)
            return domJSON.toJSON(obj, {
              metadata: false,
              serialProperties: true,
            });
          if (obj instanceof Window) return 'Window';

          const boundSerialize = serialize.bind(obj);

          if (typeof obj !== 'object' || obj === null) {
            return obj;
          }

          while (
            ancestors.length > 0 &&
            ancestors[ancestors.length - 1] !== this
          ) {
            ancestors.pop();
          }

          if (ancestors.includes(obj)) {
            return '[Circular Reference]';
          }
          ancestors.push(obj);

          if (isArrayLike(obj)) {
            obj = tryConvertToArray(obj);
          }

          if (Array.isArray(obj)) {
            const arr = obj.map((value) => {
              return boundSerialize(value, ancestors);
            });
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
          console.error(e);
          return e.toString();
        }
      };

      const startTime = Date.now();

      const _serialize = serialize.bind(null);
      const result = JSON.stringify(_serialize(obj, []));

      const endTime = Date.now();
      if (timing) {
        console.log('Serialization time: ' + (endTime - startTime) / 1000 + 's');
      }
      return result;
    },

    _getNodeId(element) {
      if (!element) {
        return null;
      }
      const pywebviewId =
        element.getAttribute('data-pywebview-id') ||
        Math.random().toString(36).substr(2, 11);
      if (!element.hasAttribute('data-pywebview-id')) {
        element.setAttribute('data-pywebview-id', pywebviewId);
      }
      return pywebviewId;
    },

    _insertNode(node, parent, mode) {
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

    _loadCss(css) {
      const interval = setInterval(() => {
        if (document.readyState === 'complete') {
          clearInterval(interval);

          const cssElement = document.createElement('style');
          cssElement.type = 'text/css';
          cssElement.innerHTML = css;
          document.head.appendChild(cssElement);
        }
      }, 10);
    },

    _processElements(elements) {
      const serializedElements = [];

      for (let i = 0; i < elements.length; i++) {
        let pywebviewId;
        if (elements[i] === window) {
          pywebviewId = 'window';
        } else if (elements[i] === document) {
          pywebviewId = 'document';
        } else {
          pywebviewId = window.pywebview._getNodeId(elements[i]);
        }

        const node = domJSON.toJSON(elements[i], {
          metadata: false,
          serialProperties: true,
          deep: false,
        });

        node._pywebviewId = pywebviewId;
        serializedElements.push(node);
      }

      return serializedElements;
    },

    _debounce(func, delay) {
      let timeout;
      return function () {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          func.apply(context, args);
        }, delay);
      };
    },
  };
}