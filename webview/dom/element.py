import logging
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict, Iterable, Optional, TYPE_CHECKING, Union
from webview.util import css_to_camel


from webview.event import EventContainer

logger = logging.getLogger('pywebview')


"""
class DOMEventContainer:
    if TYPE_CHECKING:

        @type_check_only
        def __getattr__(self, __name: str) -> DOMEvent:
            ...

        @type_check_only
        def __setattr__(self, __name: str, __value: DOMEvent) -> None:
            ...
"""

def _ignore_window_document(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0]._node_id in ('window', 'document'):
            return None

        return func(*args, **kwargs)

    return wrapper


def _check_exists(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not args[0]._exists:
            logger.warning('Element has been removed')
            return
        return func(*args, **kwargs)

    return wrapper


class Element:
    def __init__(self, window, node_id) -> None:
        self.__window = window
        self.events = EventContainer()
        self._node_id = node_id
        self._query_string = f"document.querySelector('[data-pywebview-id=\"{self._node_id}\"]')"
        self._event_handlers = defaultdict(list)
        self._event_handler_ids = {}
        self._exists = True

        self.__original_display = None
        self.__generate_events()

    @property
    @_check_exists
    def node(self) -> Dict[str, Any]:
        return self.__window.evaluate_js(f"pywebview._processElements([{self._query_string}])[0]")

    @property
    @_check_exists
    @_ignore_window_document
    def id(self) -> Optional[str]:
        return self.__window.evaluate_js(f"{self._query_string}.id")

    @id.setter
    @_check_exists
    @_ignore_window_document
    def id(self, id: str) -> None:
        self.__window.evaluate_js(f"{self._query_string}.id = '{id}'")

    @property
    @_check_exists
    @_ignore_window_document
    def classes(self) -> Iterable:
        return self.__window.evaluate_js(f"{self._query_string}.className").split(' ')

    @classes.setter
    def classes(self, classes: Iterable) -> None:
        classes = ' '.join(set(classes))
        self.__window.evaluate_js(f"{self._query_string}.className = '{classes}'")

    @property
    @_check_exists
    @_ignore_window_document
    def attributes(self) -> Dict[str, Any]:
        return self.__window.evaluate_js(f"""
            var attributes = {self._query_string}.attributes;
            var result = {{}};
            for (var i = 0; i < attributes.length; i++) {{
                result[attributes[i].name] = attributes[i].value;
            }}
            result
        """)

    @attributes.setter
    @_check_exists
    @_ignore_window_document
    def attributes(self, attributes: Dict[str, Any]) -> None:
        for name, value in attributes.items():
            self.__window.evaluate_js(f"{self._query_string}.setAttribute('{name}', '{value}')")

    @property
    @_check_exists
    @_ignore_window_document
    def style(self) -> Dict[str, Any]:
        return self.__window.evaluate_js(f"""
            var element = {self._query_string};
            var styles = window.getComputedStyle(element);
            var computedStyles = {{}};

            for (var i = 0; i < styles.length; i++) {{
                var propertyName = styles[i];
                var propertyValue = styles.getPropertyValue(propertyName);

                if (propertyValue !== '') {{
                    computedStyles[propertyName] = propertyValue;
                }}
            }}

            computedStyles;
        """)

    @style.setter
    @_check_exists
    @_ignore_window_document
    def style(self, style: Dict[str, Any]) -> None:
        converted_style = {css_to_camel(key): value for key, value in style.items()}
        self.__window.evaluate_js(f"""
            var element = {self._query_string};
            var styles = {converted_style};

            for (var key in styles) {{
                element.style[key] = styles[key];
            }}
        """)

    @property
    @_check_exists
    @_ignore_window_document
    def children(self) -> list['Element']:
        children = self.__window.evaluate_js(f"""
            var children = {self._query_string}.children;
            var nodeIds = []
            for (var i = 0; i < children.length; i++) {{
                var nodeId = pywebview._getNodeId(children[i]);
                nodeIds.push(nodeId);
            }}

            nodeIds
        """)
        return [Element(self.__window, node_id) for node_id in children]

    @property
    @_check_exists
    @_ignore_window_document
    def parent(self) -> Union['Element', None]:
        node_id = self.__window.evaluate_js(f"""
            var parent = {self._query_string}.parentElement;
            parent ? pywebview._getNodeId(parent) : null
        """)
        return Element(self.__window, node_id) if node_id else None

    @property
    @_check_exists
    @_ignore_window_document
    def next(self) -> Union['Element', None]:
        node_id = self.__window.evaluate_js(f"""
            var nextSibling = {self._query_string}.nextElementSibling;
            nextSibling ? pywebview._getNodeId(nextSibling) : null
        """)
        return Element(self.__window, node_id) if node_id else None

    @property
    @_check_exists
    @_ignore_window_document
    def previous(self) -> Union['Element', None]:
        node_id = self.__window.evaluate_js(f"""
            var previousSibling = {self._query_string}.previousElementSibling;
            previousSibling ? pywebview._getNodeId(previousSibling) : null
        """)
        return Element(self.__window, node_id) if node_id else None

    @_check_exists
    @_ignore_window_document
    def hide(self) -> None:
        self.__original_display = self.__window.evaluate_js(f"{self._query_string}.style.display")
        self.__window.evaluate_js(f"{self._query_string}.style.display = 'none'")

    @_check_exists
    @_ignore_window_document
    def show(self) -> None:
        current_display = self.__window.evaluate_js(f"{self._query_string}.style.display")

        if current_display == 'none':
            display = self.__original_display or 'block'
            self.__window.evaluate_js(f"{self._query_string}.style.display = '{display}'")

    @_check_exists
    @_ignore_window_document
    def empty(self) -> None:
        self.__window.evaluate_js(f"{self._query_string}.innerHTML = ''")

    @_check_exists
    @_ignore_window_document
    def remove(self) -> None:
        self.__window.evaluate_js(f"{self._query_string}.remove()")

        if self._node_id in self.__window.dom._elements:
            self.__window.dom._elements.pop(self._node_id)

        handler_ids = ','.join([ f'"{handler_id}"' for handler_id in self._event_handler_ids.values()])
        self.__window.evaluate_js(f"""
            var handlerIds = [{handler_ids}];
            handlerIds.forEach(function(handlerId) {{
                delete pywebview._eventHandlers[handler_id]
            }})
        """)
        self._event_handler_ids = {}
        self._event_handlers = defaultdict(list)
        self._exists = False

    @_check_exists
    @_ignore_window_document
    def toggle(self) -> None:
        current_display = self.__window.evaluate_js(f"{self._query_string}.style.display")

        if current_display == 'none':
            self.show()
        else:
            self.hide()

    @_check_exists
    def on(self, event: str, callback: Callable) -> None:
        if self._node_id not in self.__window.dom._elements:
            self.__window.dom._elements[self._node_id] = self

        handler_id = self.__window.evaluate_js(f"""
            var element = '{self._node_id}' === 'document' ? document : document.querySelector('[data-pywebview-id="{self._node_id}"]')
            var handlerId = null

            if (element) {{
                handlerId = Math.random().toString(36).substr(2, 11);
                pywebview._eventHandlers[handlerId] = function(e) {{
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

    @_check_exists
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
        del self.__window.dom._elements[self._node_id]

        for handler in self._event_handlers[event]:
            if handler == callback:
                self._event_handlers[event].remove(handler)

    @_check_exists
    def __generate_events(self):
        from webview.dom.event import DOMEvent

        events = self.__window.evaluate_js(f"""
            var mapping = {{
                'document': document,
                'window': window,
            }}

            var element = mapping['{self._node_id}'] || document.querySelector('[data-pywebview-id="{self._node_id}"]');
            Object
                .getOwnPropertyNames(element)
                .concat(
                    Object.getOwnPropertyNames(
                        Object.getPrototypeOf(
                            Object.getPrototypeOf(element)
                        )
                    )
                )
                .filter(function(i){{
                    return !i.indexOf('on') && (element[i] == null || typeof element[i]=='function');
                }})
                .map(function(f) {{ return f.substr(2) }});
        """)

        for event in events:
            setattr(self.events, event, DOMEvent(event, self.__window, self))

    @_check_exists
    def __str__(self) -> str:
        return repr(self)

    @_check_exists
    def __repr__(self) -> str:
        if self.node['nodeName'] == '#document':
            return 'document'
        elif self.node['nodeName'] == '#window':
            return 'window'
        else:
            return self.node['outerHTML']
