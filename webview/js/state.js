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
      var oldValue = target[key];
      var haltUpdate = value.hasOwnProperty('value') && value.pywebviewHaltUpdate;
      var targetValue = haltUpdate ? value.value : value;

      if (oldValue === targetValue) {
        return
      }
      debugger

      target[key] = targetValue;
      target.dispatchEvent(new CustomEvent('change', {detail: {key: key, value: targetValue}}))

      if (!haltUpdate) {
        pywebview._jsApiCallback('pywebviewStateUpdate', { key: key, value: targetValue}, (Math.random() + "").substring(2));
      }

      return true;
    },

    deleteProperty(target, key) {
      if (key in target) {
        Reflect.deleteProperty(target, key);
        delete target[key];
        console.log('delete called')
        pywebview._jsApiCallback('pywebviewStateDelete', key, (Math.random() + "").substring(2));
        console.log('delete called 2')
        target.dispatchEvent(new CustomEvent('delete', {detail: {key}}))
        return true;
      }
      return false;
    }
  })
})();