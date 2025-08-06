pywebview.state = (function() {

  function createEventTargetFromJSON(jsonString) {
    var data = JSON.parse(jsonString);
    var eventTarget = new EventTarget();

    for (var key in data) {
        if (data.hasOwnProperty(key)) {
            eventTarget[key] = data[key];
        }
    }

    return eventTarget;
}
  var initialState = '%(state)s'
  var target = createEventTargetFromJSON(initialState);

  return new Proxy(target, {
    get(obj, key) {
      var value = Reflect.get(obj, key);
      if (typeof(value) == 'function'){
        return value.bind(obj);
      }
      return value;
    },

    set(target, key, value) {
      var haltUpdate = false;
      if (key.indexOf('__pywebviewHaltUpdate__') == 0) {
        key = key.replace('__pywebviewHaltUpdate__', '');
        haltUpdate = true;
      }
      var oldValue = target[key];

      if (oldValue === value) {
        return
      }

      target[key] = value;
      target.dispatchEvent(new CustomEvent('change', {detail: {key: key, value: value}}))

      if (!haltUpdate) {
        pywebview._jsApiCallback('pywebviewStateUpdate', { key: key, value: value}, (Math.random() + "").substring(2));
      }

      return true;
    },

    deleteProperty(target, key) {
      let haltUpdate = false;
      if (key.indexOf('__pywebviewHaltUpdate__') == 0) {
        key = key.replace('__pywebviewHaltUpdate__', '');
        haltUpdate = true;
      }

      if (key in target) {
        const oldValue = target[key];
        Reflect.deleteProperty(target, key);

        delete target[key];

        if (!haltUpdate) {
          pywebview._jsApiCallback('pywebviewStateDelete', key, (Math.random() + "").substring(2));
        }
        target.dispatchEvent(new CustomEvent('delete', {detail: {key, value: oldValue}}))
        return true;
      }
      return false;
    }
  })
})();