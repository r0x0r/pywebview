class State:

    def __init__(self, window):
        self._data = {}
        self._window = window


    def __setattr__(self, name, value):
        if name != '_data':  # Prevent recursion
            old_value = self._data.get(name, None)
            if old_value != value:
                print(f"Attribute '{name}' changed from {old_value} to {value}")
            self._data[name] = value
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __delattr__(self, name):
        if name in self._data:
            print(f"Attribute '{name}' deleted")
            del self._data[name]
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # def __add__(self, item: Callable[..., Any]) -> Self:
    #     self._items.append(item)
    #     return self

    # def __sub__(self, item: Callable[..., Any]) -> Self:
    #     self._items.remove(item)
    #     return self

    # def __iadd__(self, item: Callable[..., Any]) -> Self:
    #     self._items.append(item)
    #     return self

    # def __isub__(self, item: Callable[..., Any]) -> Self:
    #     self._items.remove(item)
    #     return self