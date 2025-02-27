pywebview.state = (function() {

  function isProxy(obj) {
    if (obj === null || typeof obj != "object") return false;
    return Symbol.for("proxy") in obj;
  }

  function createEventTargetFromJSON(jsonString) {
    var data = JSON.parse(jsonString);
    var eventTarget = new EventTarget();

    for (var key in data) {
        if (data.hasOwnProperty(key)) {
            eventTarget[key] = wrapValue(data[key], key, eventTarget);
        }
    }

    return eventTarget;
  }

  function wrapValue(value, path, parentTarget) {
    if (typeof value === 'object' && value !== null) {
      if (Array.isArray(value)) {
        return createObservableArray(value, path, parentTarget);
      } else {
        return createObservableObject(value, path, parentTarget);
      }
    }
    return value;
  }

  function createObservableObject(obj, parentPath, parentTarget) {
    var proxy = new Proxy(obj, {
      has(o, prop) {
        if(prop == Symbol.for("proxy")) return true;
        return prop in o;
      },

      get(target, key) {
        var value = Reflect.get(target, key);
        if (typeof value === 'function') {
          return value.bind(target);
        }
        // Ensure nested objects are wrapped when accessed
        if (typeof value === 'object' && value !== null && !isProxy(value)) {
          value = wrapValue(value, getFullPath(parentPath, key), parentTarget);
          Reflect.set(target, key, value);
        }
        return value;
      },

      set(target, key, value) {
        var fullPath = getFullPath(parentPath, key);
        var oldValue = target[key];
        if (oldValue === value) {
          return true;
        }
        console.log('set obs obj: ', key, value)
        value = wrapValue(value, fullPath, parentTarget);
        Reflect.set(target, key, value);

        parentTarget.dispatchEvent(new CustomEvent('change', { detail: { key: fullPath, value: value } }));
        if (key.indexOf('__pywebviewHaltUpdate__') !== -1) {
          pywebview._jsApiCallback('pywebviewStateUpdate', { key: fullPath, value: value }, (Math.random() + "").substring(2));
        }

        return true;
      },

      deleteProperty(target, key) {
        var fullPath = getFullPath(parentPath, key);
        if (key in target) {
          Reflect.deleteProperty(target, key);
          parentTarget.dispatchEvent(new CustomEvent('delete', { detail: { key: fullPath } }));

          if (!key.startsWith('__pywebviewHaltUpdate__')) {
            pywebview._jsApiCallback('pywebviewStateDelete', fullPath, (Math.random() + "").substring(2));
          }

          return true;
        }
        return false;
      }
    });

    return proxy;
  }

  function createObservableArray(arr, parentPath, parentTarget) {
    var proxy = new Proxy(arr, {
      has(o, prop) {
        if (prop == Symbol.for("proxy")) return true;
        return prop in o;
      },

      get(target, key) {
        var value = Reflect.get(target, key);
        if (typeof value === 'function') {
          return value.bind(target);
        }
        // Ensure nested objects are wrapped when accessed
        if (typeof value === 'object' && value !== null && !isProxy(value)) {
          value = wrapValue(value, getFullPath(parentPath, key), parentTarget);
          Reflect.set(target, key, value);
        }
        return value;
      },

      set(target, key, value) {
        var fullPath = getFullPath(parentPath, key);
        var oldValue = target[key];
        if (oldValue === value) {
          return true;
        }

        value = wrapValue(value, fullPath, parentTarget);
        Reflect.set(target, key, value);

        parentTarget.dispatchEvent(new CustomEvent('change', { detail: { key: fullPath, value: value } }));

        if (!key.startsWith('__pywebviewHaltUpdate__')) {
          console.log('set obs array: ', key, value)
          pywebview._jsApiCallback('pywebviewStateUpdate', { key: fullPath, value: value }, (Math.random() + "").substring(2));
        }

        return true;
      },

      deleteProperty(target, key) {
        var fullPath = getFullPath(parentPath, key);
        if (key in target) {
          Reflect.deleteProperty(target, key);
          parentTarget.dispatchEvent(new CustomEvent('delete', { detail: { key: fullPath } }));

          if (!key.startsWith('__pywebviewHaltUpdate__')) {
            pywebview._jsApiCallback('pywebviewStateDelete', fullPath, (Math.random() + "").substring(2));
          }

          return true;
        }
        return false;
      }
    });

    return proxy;
  }

  function getFullPath(parentPath, key) {
    if (parentPath) {
      if (typeof key === 'number' || key.match(/^\d+$/)) {
        return `${parentPath}[${key}]`;
      } else {
        return `${parentPath}.${key}`;
      }
    }
    return key;
  }

  var initialState = '%(state)s';
  var eventTarget = createEventTargetFromJSON(initialState);

  return new Proxy(eventTarget, {
    has(o, prop) {
      if (prop == Symbol.for("proxy")) return true;
      return prop in o;
    },

    get(obj, key) {
      if (key.indexOf('__pywebviewHaltUpdate__') > -1) {
        key = key.replace('__pywebviewHaltUpdate__', '');
      }
      var value = Reflect.get(obj, key);
      if (typeof value === 'function') {
        return value.bind(obj);
      }
      return value;
    },

    set(target, key, value) {
      var haltUpdate = false;
      if (key.indexOf('__pywebviewHaltUpdate__') > -1) {
        key = key.replace('__pywebviewHaltUpdate__', '');
        haltUpdate = true;
      }
      var oldValue = target[key];

      if (oldValue === value) {
        return true;
      }

      value = wrapValue(value, key, eventTarget);
      Reflect.set(target, key, value);

      eventTarget.dispatchEvent(new CustomEvent('change', { detail: { key: key, value: value } }));

      if (!haltUpdate) {
        pywebview._jsApiCallback('pywebviewStateUpdate', { key: key, value: value }, (Math.random() + "").substring(2));
      }

      return true;
    },

    deleteProperty(target, key) {
      let haltUpdate = false;
      if (key.indexOf('__pywebviewHaltUpdate__') > -1) {
        key = key.replace('__pywebviewHaltUpdate__', '');
        haltUpdate = true;
      }

      if (key in target) {
        Reflect.deleteProperty(target, key);
        delete target[key];

        if (!haltUpdate) {
          pywebview._jsApiCallback('pywebviewStateDelete', key, (Math.random() + "").substring(2));
        }
        eventTarget.dispatchEvent(new CustomEvent('delete', { detail: { key: key } }));
        return true;
      }
      return false;
    }
  });
})();