
window.testUtils = {
    resetState: () => {
        if (window.pywebview && window.pywebview.state) {
            // Get all keys from state and delete them, except predefined ones
            const predefinedKeys = ['number', 'message', 'dict', 'list', 'nested'];
            const keys = Object.keys(window.pywebview.state);
            keys.forEach(key => {
                if (!predefinedKeys.includes(key)) {
                    delete window.pywebview.state[key];
                }
            });

            // Reset predefined state to original values from runner.py
            if (window.pywebview.state.number !== undefined) {
                window.pywebview.state.number = 0;
            }
            if (window.pywebview.state.message !== undefined) {
                window.pywebview.state.message = 'test';
            }
            if (window.pywebview.state.dict !== undefined) {
                window.pywebview.state.dict = {'key': 'value'};
            }
            if (window.pywebview.state.list !== undefined) {
                window.pywebview.state.list = [1, 2, 3];
            }
            if (window.pywebview.state.nested !== undefined) {
                window.pywebview.state.nested = {
                    'a': 1,
                    'b': [1, 2, 3],
                    'c': {'d': 4}
                };
            }
        }
    },

    setCookie: (name, value, days = 7, path = '/') => {
      const expires = new Date(Date.now() + days * 864e5).toUTCString();
      document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=${path}`;
    },

    wait: (ms) => {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

