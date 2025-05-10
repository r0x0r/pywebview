import logging

from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from webview.dom import DOMEventHandler, ManipulationMode
from webview.dom.classlist import ClassList
from webview.dom import _dnd_state
from webview.dom.propsdict import DOMPropType, PropsDict
from webview.errors import JavascriptException
from webview.event import EventContainer

logger = logging.getLogger('pywebview')


def _ignore_window_document(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0]._node_id in ('window', 'document'):
            return None

        return func(*args, **kwargs)

    return wrapper


def _exists(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not args[0]._exists:
            logger.warning(f'Element with id {args[0]._node_id} has been removed')
            return

        try:
            return func(*args, **kwargs)
        except JavascriptException as e:
            if e.args[0].get('cause') == 'ELEMENT_NOT_FOUND':
                logger.warning(f'Element with id {args[0]._node_id} has been removed')
            else:
                logger.exception(e)
            return

    return wrapper


class Element:
    def __init__(self, window, node_id) -> None:
        self._window = window
        self.events = EventContainer()
        self._node_id = node_id
        self._query_command = rf"""
            var element;

            if ('{self._node_id}' === 'document') {{
                element = document;
            }} else if ('{self._node_id}' === 'window') {{
                element = window;
            }} else if ('{self._node_id}' === 'body') {{
                element = document.body;
            }} else {{
                element = document.querySelector('[data-pywebview-id="{self._node_id}"]');
            }}

            if (!element) {{
                throw new Error('Element with pywebview-id {self._node_id} not found', {{ cause: 'ELEMENT_NOT_FOUND' }});
            }}
        """.replace('\n', '')
        self._event_handlers = defaultdict(list)
        self._event_handler_ids = {}
        self._exists = True
        self._classes = ClassList(self)
        self._style = PropsDict(self, DOMPropType.Style)
        self._attributes = PropsDict(self, DOMPropType.Attribute)

        self.__original_display = None
        self.__generate_events()

    @property
    @_exists
    @_ignore_window_document
    def tag(self) -> str:
        return self._window.evaluate_js(f"{self._query_command}; element.tagName").lower()

    @property
    @_exists
    @_ignore_window_document
    def id(self) -> Optional[str]:
        return self._window.evaluate_js(f"{self._query_command}; element.id")

    @id.setter
    @_exists
    @_ignore_window_document
    def id(self, id: str) -> None:
        self._window.run_js(f"{self._query_command}; element.id = '{id}'")

    @property
    @_exists
    @_ignore_window_document
    def classes(self) -> ClassList:
        return self._classes

    @classes.setter
    def classes(self, classes: Iterable) -> None:
        self._classes = ClassList(self, classes)

    @property
    @_exists
    @_ignore_window_document
    def attributes(self) -> Dict[str, Any]:
        return self._attributes

    @attributes.setter
    @_exists
    @_ignore_window_document
    def attributes(self, attributes: Dict[str, Any]) -> None:
        self._attributes = PropsDict(self, DOMPropType.Attribute, attributes)

    @property
    @_exists
    def node(self) -> Dict[str, Any]:
        return self._window.evaluate_js(f"{self._query_command}; var r2 = pywebview._processElements([element])[0]; r2")

    @property
    @_exists
    @_ignore_window_document
    def style(self) -> Dict[str, Any]:
        return self._style

    @style.setter
    @_exists
    @_ignore_window_document
    def style(self, style: Dict[str, Any]) -> None:
        self._style = PropsDict(self, DOMPropType.Style, style)

    @property
    @_exists
    @_ignore_window_document
    def tabindex(self) -> int:
        return self._window.evaluate_js(f"{self._query_command}; element.tabIndex")

    @tabindex.setter
    @_exists
    @_ignore_window_document
    def tabindex(self, tab_index: int) -> None:
        self._window.run_js(f"{self._query_command}; element.tabIndex = {tab_index}")

    @property
    @_exists
    @_ignore_window_document
    def text(self) -> str:
        return self._window.evaluate_js(f"{self._query_command}; element.textContent")

    @text.setter
    @_exists
    @_ignore_window_document
    def text(self, text: str) -> None:
        self._window.run_js(f"{self._query_command}; element.textContent = '{text}'")

    @property
    @_exists
    @_ignore_window_document
    def value(self) -> str:
        return self._window.evaluate_js(f"{self._query_command}; element.value")

    @property
    @_exists
    @_ignore_window_document
    def visible(self) -> bool:
        return self._window.evaluate_js(f"{self._query_command}; element.offsetParent !== null")

    @property
    @_exists
    @_ignore_window_document
    def focused(self) -> bool:
        return self._window.evaluate_js(f"{self._query_command}; document.activeElement === element")

    @value.setter
    @_exists
    @_ignore_window_document
    def value(self, value: str) -> None:
        self._window.run_js(f"{self._query_command}; if ('value' in element) {{ element.value = '{value}' }}")

    @_exists
    @_ignore_window_document
    def blur(self) -> None:
        self._window.run_js(f"{self._query_command}; element.blur()")

    @_exists
    @_ignore_window_document
    def focus(self) -> None:
        self._window.run_js(f"{self._query_command}; element.focus()")

    @property
    @_exists
    @_ignore_window_document
    def children(self) -> List['Element']:
        children = self._window.evaluate_js(f"""
            {self._query_command};
            var children = element.children;
            var nodeIds = []
            for (var i = 0; i < children.length; i++) {{
                var nodeId = pywebview._getNodeId(children[i]);
                nodeIds.push(nodeId);
            }}

            nodeIds
        """)
        return [Element(self._window, node_id) for node_id in children]

    @property
    @_exists
    @_ignore_window_document
    def parent(self) -> Union['Element', None]:
        node_id = self._window.evaluate_js(f"""
            {self._query_command};
            var parent = element.parentElement;
            parent ? pywebview._getNodeId(parent) : null
        """)
        return Element(self._window, node_id) if node_id else None

    @property
    @_exists
    @_ignore_window_document
    def next(self) -> Union['Element', None]:
        node_id = self._window.evaluate_js(f"""
            {self._query_command};
            var nextSibling = element.nextElementSibling;
            nextSibling ? pywebview._getNodeId(nextSibling) : null
        """)
        return Element(self._window, node_id) if node_id else None

    @property
    @_exists
    @_ignore_window_document
    def previous(self) -> Union['Element', None]:
        node_id = self._window.evaluate_js(f"""
            {self._query_command};
            var previousSibling = element.previousElementSibling;
            previousSibling ? pywebview._getNodeId(previousSibling) : null
        """)
        return Element(self._window, node_id) if node_id else None

    @_exists
    @_ignore_window_document
    def hide(self) -> None:
        self.__original_display = self._window.evaluate_js(f"{self._query_command}; element.style.display")
        self._window.run_js(f"{self._query_command}; element.style.display = 'none'")

    @_exists
    @_ignore_window_document
    def show(self) -> None:
        current_display = self._window.evaluate_js(f"{self._query_command}; element.style.display")

        if current_display == 'none':
            display = self.__original_display or 'block'
            self._window.run_js(f"{self._query_command}; element.style.display = '{display}'")

    @_exists
    @_ignore_window_document
    def toggle(self) -> None:
        current_display = self._window.evaluate_js(f"{self._query_command}; element.style.display")

        if current_display == 'none':
            self.show()
        else:
            self.hide()

    @_exists
    @_ignore_window_document
    def append(self, html: str, mode=ManipulationMode.LastChild) -> 'Element':
        return self._window.dom.create_element(html, self, mode)

    @_exists
    @_ignore_window_document
    def empty(self) -> None:
        self._window.run_js(f"{self._query_command}; element.innerHTML = ''")

    @_exists
    @_ignore_window_document
    def remove(self) -> None:
        self._window.run_js(f"{self._query_command}; element.remove()")

        if self._node_id in self._window.dom._elements:
            self._window.dom._elements.pop(self._node_id)

        handler_ids = ','.join([ f'"{handler_id}"' for handler_id in self._event_handler_ids.values()])
        self._window.run_js(f"""
            var handlerIds = [{handler_ids}];
            handlerIds.forEach(function(handlerId) {{
                delete pywebview._eventHandlers[handler_id]
            }})
        """)
        self._event_handler_ids = {}
        self._event_handlers = defaultdict(list)
        self._exists = False

    @_exists
    @_ignore_window_document
    def copy(self, target: Union[str, 'Element']=None, mode=ManipulationMode.LastChild, id: str=None) -> 'Element':
        if isinstance(target, str):
            target = self._window.dom.get_element(target)
        elif target is None:
            target = self.parent

        if id:
            id_command = f'newElement.id = "{id}"'
        else:
            id_command = 'newElement.removeAttribute("id")'

        node_id = self._window.evaluate_js(f"""
            {self._query_command};
            var target = document.querySelector('[data-pywebview-id=\"{target._node_id}\"]');
            var newElement = element.cloneNode(true);
            newElement.removeAttribute('data-pywebview-id');
            {id_command};

            var nodeId = pywebview._getNodeId(newElement);
            pywebview._insertNode(newElement, target, '{mode.value}')
            nodeId;
        """)

        new_element = Element(self._window, node_id)
        for event, handlers in self._event_handlers.items():
            for handler in handlers:
                new_element.on(event, handler)

        return new_element

    @_exists
    @_ignore_window_document
    def move(self, target: Union[str, 'Element'], mode=ManipulationMode.LastChild) -> 'Element':
        if isinstance(target, str):
            target = self._window.dom.get_element(target)

        self._window.run_js(f"""
            {self._query_command};
            var target = document.querySelector('[data-pywebview-id=\"{target._node_id}\"]');
            pywebview._insertNode(element, target, '{mode.value}')
        """)
        return self

    @_exists
    def on(self, event: str, callback: Union[Callable, DOMEventHandler]) -> None:
        if self._node_id not in self._window.dom._elements:
            self._window.dom._elements[self._node_id] = self

        if isinstance(callback, DOMEventHandler):
            prevent_default = 'e.preventDefault();' if callback.prevent_default else ''
            stop_propagation = 'e.stopPropagation();' if callback.stop_propagation else ''
            debounce = callback.debounce
            callback = callback.callback
        else:
            prevent_default = ''
            stop_propagation = ''
            debounce = 0

        callback_func = f"window.pywebview._jsApiCallback('pywebviewEventHandler', {{ event: e, nodeId: '{self._node_id}' }}, 'eventHandler')"
        debounced_func = (
            f'pywebview._debounce(function() {{ {callback_func} }}, {debounce})'
            if debounce > 0
            else callback_func
        )

        handler_id = self._window.evaluate_js(f"""
            {self._query_command};
            var handlerId = null

            if (element) {{
                handlerId = Math.random().toString(36).substr(2, 11);
                pywebview._eventHandlers[handlerId] = function(e) {{
                    {prevent_default}
                    {stop_propagation}
                    {debounced_func};
                }}

                element.addEventListener('{event}', pywebview._eventHandlers[handlerId]);
            }};
            handlerId;
        """)

        if handler_id:
            self._event_handlers[event].append(callback)
            self._event_handler_ids[callback] = handler_id

        if event == 'drop':
            _dnd_state['num_listeners'] += 1

    @_exists
    def off(self, event: str, callback: Callable) -> None:
        handler_id = self._event_handler_ids.get(callback)

        if not handler_id:
            return

        self._window.run_js(f"""
            {self._query_command};
            var callback = pywebview._eventHandlers['{handler_id}'];
            if (element) {{
                element.removeEventListener('{event}', callback);
                delete pywebview._eventHandlers['{handler_id}'];
            }}
        """)

        del self._event_handler_ids[callback]
        del self._window.dom._elements[self._node_id]

        for handler in self._event_handlers[event]:
            if handler == callback:
                self._event_handlers[event].remove(handler)

        if event == 'drop':
            _dnd_state['num_listeners'] = max(0, _dnd_state['num_listeners'] - 1)

    @_exists
    def __generate_events(self):
        from webview.dom.event import DOMEvent

        events = self._window.evaluate_js(f"""
            {self._query_command};
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
            setattr(self.events, event, DOMEvent(event, self))

    @_exists
    def __str__(self) -> str:
        return repr(self)

    @_exists
    def __repr__(self) -> str:
        if self.node['nodeName'] == '#document':
            return 'document'
        elif self.node['nodeName'] == '#window':
            return 'window'
        else:
            return self.node['outerHTML']

    @_exists
    def __eq__(self, other: 'Element') -> bool:
        return hasattr(other, '_node_id') and self._node_id == other._node_id
