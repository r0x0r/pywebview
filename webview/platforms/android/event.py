class EventDispatcher:
    __event_stack = {}

    def register_event_type(self, event_type):
        """Register an event type with the dispatcher.
        Registering event types allows the dispatcher to validate event handler
        names as they are attached and to search attached objects for suitable
        handlers. Each event type declaration must:
            1. start with the prefix `on_`.
            2. have a default handler in the class.
        """

        if event_type[:3] != 'on_':
            raise Exception('A new event must start with "on_"')

        # Ensure that the user has at least declared the default handler
        if not hasattr(self, event_type):
            raise Exception(
                f'Missing default handler {event_type} in {self.__class__.__name__}')

        # Add the event type to the stack
        if event_type not in self.__event_stack:
            self.__event_stack[event_type] = []

    def unregister_event_type(self, event_type):
        pass

    def bind(self, **kwargs):
        for key, value in kwargs.items():
            assert callable(value), '{!r} is not callable'.format(value)
            if key[:3] == 'on_':
                observers: list = self.__event_stack.get(key)
                if observers is None:
                    continue
                observers.append(value)

    def unbind(self, **kwargs):
        """Unbind event from callback functions with similar usage as"""

        for key, value in kwargs.items():
            if key[:3] == 'on_':
                observers: list = self.__event_stack.get(key)
                if observers is None:
                    continue
                observers.remove(value)

    def is_event_type(self, event_type):
        """Return True if the event_type is already registered.
        """
        return event_type in self.__event_stack

    def dispatch(self, event_type, *args, **kwargs):
        """Dispatch an event across all the handlers added in bind/fbind().
        As soon as a handler returns True, the dispatching stops.
        The function collects all the positional and keyword arguments and
        passes them on to the handlers.
        .. note::
           The handlers are called in reverse order than they were registered
           with :meth:`bind`.
        :Parameters:
           `event_type`: str
               the event name to dispatch.
        .. versionchanged:: 1.9.0
           Keyword arguments collection and forwarding was added. Before, only
           positional arguments would be collected and forwarded.
        """
        observers: list = self.__event_stack.get(event_type)
        observers.reverse()
        for callbacks in observers:
            callbacks(*args, **kwargs)

        handler = getattr(self, event_type)
        return handler(*args, **kwargs)
