export function initState() {
  pywebview.state = (() => {

    const createEventTargetFromJSON = (jsonString) => {
      const data = JSON.parse(jsonString);
      const eventTarget = new EventTarget();

      for (const key in data) {
          if (data.hasOwnProperty(key)) {
              eventTarget[key] = data[key];
          }
      }

      return eventTarget;
    };

    const initialState = '%(state)s';
    const target = createEventTargetFromJSON(initialState);
    alert('woot')
    try {
      return new Proxy(target, {
        get(obj, key) {
          const value = Reflect.get(obj, key);
          if (typeof(value) == 'function'){
            return value.bind(obj);
          }
          return value;
        },

        set(target, key, value) {
          let haltUpdate = false;
          if (key.indexOf('__pywebviewHaltUpdate__') == 0) {
            key = key.replace('__pywebviewHaltUpdate__', '');
            haltUpdate = true;
          }
          const oldValue = target[key];

          if (oldValue === value) {
            return;
          }

          target[key] = value;
          target.dispatchEvent(new CustomEvent('change', {detail: {key, value}}));

          if (!haltUpdate) {
            pywebview._jsApiCallback('pywebviewStateUpdate', { key, value }, (Math.random() + "").substring(2));
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
            target.dispatchEvent(new CustomEvent('delete', {detail: {key, value: oldValue}}));
            return true;
          }
          return false;
        }
      });
    } catch (e) {
      console.error('Error creating state proxy:', e);
      return {}
    }
  })()
}