from collections import defaultdict
from typing import Any, Callable, Dict, Optional


class Element:
    def __init__(self, window, node: Optional[Dict[str, Any]]) -> None:
        self.__window = window
        self.node = node
        self._node_id = node['_pywebviewId']
        self._event_handlers = defaultdict(list)
        self._event_handler_ids = {}

        del self.node['_pywebviewId']

    def on(self, event: str, callback: Callable) -> None:
        handler_id = self.__window.evaluate_js(f"""
            var element = '{self._node_id}' === 'document' ? document : document.querySelector('[data-pywebview-id="{self._node_id}"]')
            var handlerId = null

            if (element) {{
                handlerId = Math.random().toString(36).substr(2, 11);
                pywebview._eventHandlers[handlerId] = function(e) {{
                    debugger
                    window.pywebview._bridge.call('pywebviewEventHandler', {{ event: e, nodeId: '{self._node_id}' }}, 'eventHandler');
                }}

                element.addEventListener('{event}', pywebview._eventHandlers[handlerId]);
            }};
            handlerId;
        """)

        if not handler_id:
            raise ValueError(f'Element with pywebview-id {self._node_id} not found')
        else:
            self._event_handlers[event].append(callback)
            self._event_handler_ids[callback] = handler_id

    def off(self, event: str, callback: Callable) -> None:
        handler_id = self._event_handler_ids.get(callback)

        if not handler_id:
            return

        self.__window.evaluate_js(f"""
            var nodeId = '{self._node_id}';
            var element = nodeId === 'document' ? document : document.querySelector('[data-pywebview-id="{self._node_id}"]');
            var callback = pywebview._eventHandlers['{handler_id}'];
            if (element) {{
                element.removeEventListener('{event}', callback);
                delete pywebview._eventHandlers['{handler_id}'];
            }}
        """)

        del self._event_handler_ids[callback]
        for handler in self._event_handlers[event]:
            if handler == callback:
                self._event_handlers[event].remove(handler)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return '(%s, %s)' % (self.width, self.height)
