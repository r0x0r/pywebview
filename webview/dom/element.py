import json
import logging

from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict, Iterable, Optional, TYPE_CHECKING, Union
from webview.util import JavascriptException, css_to_camel, escape_quotes


from webview.event import EventContainer

logger = logging.getLogger('pywebview')


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
        self.__window = window
        self.events = EventContainer()
        self._node_id = node_id
        self._query_command = rf"""
            var element;

            if ('{self._node_id}' === 'document') {{
                element = document;
            }} else if ('{self._node_id}' === 'window') {{
                element = window;
            }} else {{
                element = document.querySelector('[data-pywebview-id=\"{self._node_id}\"]');
            }}

            if (!element) {{
                throw new Error('Element with pywebview-id {self._node_id} not found', {{ cause: 'ELEMENT_NOT_FOUND' }});
            }}
        """.replace('\n', '')
        self._event_handlers = defaultdict(list)
        self._event_handler_ids = {}
        self._exists = True

        self.__original_display = None
        self.__generate_events()

    @property
    @_check_exists
    @_ignore_window_document
    def tag(self) -> str:
        return self.__window.evaluate_js(f"{self._query_command}; element.tagName").lower()

    @property
    @_check_exists
    @_ignore_window_document
    def id(self) -> Optional[str]:
        return self.__window.evaluate_js(f"{self._query_command}; element.id")

    @id.setter
    @_check_exists
    @_ignore_window_document
    def id(self, id: str) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.id = '{id}'")

    @property
    @_check_exists
    @_ignore_window_document
    def classes(self) -> Iterable:
        return self.__window.evaluate_js(f"{self._query_command}; element.className").split(' ')

    @classes.setter
    def classes(self, classes: Iterable) -> None:
        classes = ' '.join(set(classes))
        self.__window.evaluate_js(f"{self._query_command}; element.className = '{classes}'")

    @property
    @_check_exists
    @_ignore_window_document
    def attributes(self) -> Dict[str, Any]:
        return self.__window.evaluate_js(f"""
            {self._query_command};
            var attributes = element.attributes;
            var result = {{}};
            for (var i = 0; i < attributes.length; i++) {{
                if (attributes[i].name === 'data-pywebview-id') {{
                    continue;
                }}
                result[attributes[i].name] = attributes[i].value;
            }}
            result
        """)

    @attributes.setter
    @_check_exists
    @_ignore_window_document
    def attributes(self, attributes: Dict[str, Any]) -> None:
        converted_attributes = json.dumps({
            escape_quotes(key): escape_quotes(value) for key, value in attributes.items()
        })

        self.__window.evaluate_js(f"""
            {self._query_command};
            var attributes = JSON.parse('{converted_attributes}');

            for (var key in attributes) {{
                if (key === 'data-pywebview-id') {{
                    continue;
                }} else if (attributes[key] === null || attributes[key] === undefined) {{
                    element.removeAttribute(key);
                }} else {{
                    element.setAttribute(key, attributes[key]);
                }}
            }};
        """)

    @_check_exists
    def node(self) -> Dict[str, Any]:
        return self.__window.evaluate_js(f"{self._query_command}; pywebview._processElements([element])[0]")

    @property
    @_check_exists
    @_ignore_window_document
    def style(self) -> Dict[str, Any]:
        return self.__window.evaluate_js(f"""
            {self._query_command};
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
        converted_style = json.dumps({css_to_camel(key): value for key, value in style.items()})
        self.__window.evaluate_js(f"""
            {self._query_command};
            var styles = JSON.parse('{converted_style}');

            for (var key in styles) {{
                element.style[key] = styles[key];
            }}
        """)

    @property
    @_check_exists
    @_ignore_window_document
    def tabindex(self) -> int:
        return self.__window.evaluate_js(f"{self._query_command}; element.tabIndex")

    @tabindex.setter
    @_check_exists
    @_ignore_window_document
    def tabindex(self, tab_index: int) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.tabIndex = {tab_index}")

    @property
    @_check_exists
    @_ignore_window_document
    def text(self) -> str:
        return self.__window.evaluate_js(f"{self._query_command}; element.textContent")

    @text.setter
    @_check_exists
    @_ignore_window_document
    def text(self, text: str) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.textContent = '{text}'")

    @property
    @_check_exists
    @_ignore_window_document
    def value(self) -> str:
        return self.__window.evaluate_js(f"{self._query_command}; element.value")

    @property
    @_check_exists
    @_ignore_window_document
    def visible(self) -> bool:
        return self.__window.evaluate_js(f"{self._query_command}; element.offsetParent !== null")

    @property
    @_check_exists
    @_ignore_window_document
    def focused(self) -> bool:
        return self.__window.evaluate_js(f"{self._query_command}; document.activeElement === element")

    @value.setter
    @_check_exists
    @_ignore_window_document
    def value(self, value: str) -> None:
        self.__window.evaluate_js(f"{self._query_command}; if ('value' in element) {{ element.value = '{value}' }}")

    @_check_exists
    @_ignore_window_document
    def add_class(self, class_name: str) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.classList.add('{class_name}')")

    @_check_exists
    @_ignore_window_document
    def remove_class(self, class_name: str) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.classList.remove('{class_name}')")

    @_check_exists
    @_ignore_window_document
    def toggle_class(self, class_name: str) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.classList.toggle('{class_name}')")

    @_check_exists
    @_ignore_window_document
    def blur(self) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.blur()")

    @_check_exists
    @_ignore_window_document
    def focus(self) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.focus()")

    @property
    @_check_exists
    @_ignore_window_document
    def children(self) -> list['Element']:
        children = self.__window.evaluate_js(f"""
            {self._query_command};
            var children = element.children;
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
            {self._query_command};
            var parent = element.parentElement;
            parent ? pywebview._getNodeId(parent) : null
        """)
        return Element(self.__window, node_id) if node_id else None

    @property
    @_check_exists
    @_ignore_window_document
    def next(self) -> Union['Element', None]:
        node_id = self.__window.evaluate_js(f"""
            {self._query_command};
            var nextSibling = element.nextElementSibling;
            nextSibling ? pywebview._getNodeId(nextSibling) : null
        """)
        return Element(self.__window, node_id) if node_id else None

    @property
    @_check_exists
    @_ignore_window_document
    def previous(self) -> Union['Element', None]:
        node_id = self.__window.evaluate_js(f"""
            {self._query_command};
            var previousSibling = element.previousElementSibling;
            previousSibling ? pywebview._getNodeId(previousSibling) : null
        """)
        return Element(self.__window, node_id) if node_id else None

    @_check_exists
    @_ignore_window_document
    def hide(self) -> None:
        self.__original_display = self.__window.evaluate_js(f"{self._query_command}; element.style.display")
        self.__window.evaluate_js(f"{self._query_command}; element.style.display = 'none'")

    @_check_exists
    @_ignore_window_document
    def show(self) -> None:
        current_display = self.__window.evaluate_js(f"{self._query_command}; element.style.display")

        if current_display == 'none':
            display = self.__original_display or 'block'
            self.__window.evaluate_js(f"{self._query_command}; element.style.display = '{display}'")

    @_check_exists
    @_ignore_window_document
    def append(self, html: str) -> 'Element':
        return self.__window.dom.create_element(html, self)

    @_check_exists
    @_ignore_window_document
    def empty(self) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.innerHTML = ''")

    @_check_exists
    @_ignore_window_document
    def remove(self) -> None:
        self.__window.evaluate_js(f"{self._query_command}; element.remove()")

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
        current_display = self.__window.evaluate_js(f"{self._query_command}; element.style.display")

        if current_display == 'none':
            self.show()
        else:
            self.hide()

    @_check_exists
    def on(self, event: str, callback: Callable) -> None:
        if self._node_id not in self.__window.dom._elements:
            self.__window.dom._elements[self._node_id] = self

        handler_id = self.__window.evaluate_js(f"""
            {self._query_command};
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

        if handler_id:
            self._event_handlers[event].append(callback)
            self._event_handler_ids[callback] = handler_id

    @_check_exists
    def off(self, event: str, callback: Callable) -> None:
        handler_id = self._event_handler_ids.get(callback)

        if not handler_id:
            return

        self.__window.evaluate_js(f"""
            {self._query_command};
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
