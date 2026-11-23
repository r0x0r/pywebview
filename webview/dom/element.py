import json
import logging
import secrets
from collections import defaultdict
from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any, TypeVar, Union, cast

from webview.dom import DOMEventHandler, ManipulationMode, _dnd_state
from webview.dom.classlist import ClassList
from webview.dom.propsdict import DOMPropType, PropsDict
from webview.errors import JavascriptException, WebViewException
from webview.event import EventContainer
from webview.util import escape_string

logger = logging.getLogger('pywebview')

F = TypeVar('F', bound=Callable[..., Any])


def _ignore_window_document(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0]._node_id in ('window', 'document'):
            return None

        return func(*args, **kwargs)

    return cast(F, wrapper)


def _exists(func: F) -> F:
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

    return cast(F, wrapper)


class Element:
    def __init__(self, window: Any, node_id: str) -> None:
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
        self._event_handlers: defaultdict[str, list[Callable[..., Any]]] = defaultdict(list)
        # listener id -> (event, callback); the same callback may be registered more than once
        self._event_listeners: dict[str, tuple[str, Callable[..., Any]]] = {}
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
        return self._window.evaluate_js(f'{self._query_command}; element.tagName').lower()

    @property
    @_exists
    @_ignore_window_document
    def id(self) -> str | None:
        return self._window.evaluate_js(f'{self._query_command}; element.id')

    @id.setter
    @_exists
    @_ignore_window_document
    def id(self, id: str) -> None:
        self._window.run_js(f"{self._query_command}; element.id = '{escape_string(id)}'")

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
    def attributes(self) -> PropsDict:
        return self._attributes

    @attributes.setter
    @_exists
    @_ignore_window_document
    def attributes(self, attributes: dict[str, Any]) -> None:
        self._attributes = PropsDict(self, DOMPropType.Attribute, attributes)

    @property
    @_exists
    def node(self) -> dict[str, Any]:
        return self._window.evaluate_js(
            f'{self._query_command}; var r2 = pywebview._processElements([element])[0]; r2'
        )

    @property
    @_exists
    @_ignore_window_document
    def style(self) -> PropsDict:
        return self._style

    @style.setter
    @_exists
    @_ignore_window_document
    def style(self, style: dict[str, Any]) -> None:
        self._style = PropsDict(self, DOMPropType.Style, style)

    @property
    @_exists
    @_ignore_window_document
    def tabindex(self) -> int:
        return self._window.evaluate_js(f'{self._query_command}; element.tabIndex')

    @tabindex.setter
    @_exists
    @_ignore_window_document
    def tabindex(self, tab_index: int) -> None:
        self._window.run_js(f'{self._query_command}; element.tabIndex = {tab_index}')

    @property
    @_exists
    @_ignore_window_document
    def text(self) -> str:
        return self._window.evaluate_js(f'{self._query_command}; element.textContent')

    @text.setter
    @_exists
    @_ignore_window_document
    def text(self, text: str) -> None:
        self._window.run_js(f"{self._query_command}; element.textContent = '{escape_string(text)}'")

    @property
    @_exists
    @_ignore_window_document
    def value(self) -> str:
        return self._window.evaluate_js(f'{self._query_command}; element.value')

    @value.setter
    @_exists
    @_ignore_window_document
    def value(self, value: str) -> None:
        self._window.run_js(
            f"{self._query_command}; if ('value' in element) {{ element.value = '{escape_string(value)}' }}"
        )

    @property
    @_exists
    @_ignore_window_document
    def visible(self) -> bool:
        return self._window.evaluate_js(f'{self._query_command}; element.offsetParent !== null')

    @property
    @_exists
    @_ignore_window_document
    def focused(self) -> bool:
        return self._window.evaluate_js(
            f'{self._query_command}; document.activeElement === element'
        )

    @_exists
    @_ignore_window_document
    def blur(self) -> None:
        self._window.run_js(f'{self._query_command}; element.blur()')

    @_exists
    @_ignore_window_document
    def focus(self) -> None:
        self._window.run_js(f'{self._query_command}; element.focus()')

    @property
    @_exists
    @_ignore_window_document
    def children(self) -> list['Element']:
        children = self._window.evaluate_js(
            f"""
            {self._query_command};
            var children = element.children;
            var nodeIds = []
            for (var i = 0; i < children.length; i++) {{
                var nodeId = pywebview._getNodeId(children[i]);
                nodeIds.push(nodeId);
            }}

            nodeIds
        """
        )
        return [Element(self._window, node_id) for node_id in children]

    @property
    @_exists
    @_ignore_window_document
    def parent(self) -> Union['Element', None]:
        return self.__related('parentElement')

    @property
    @_exists
    @_ignore_window_document
    def next(self) -> Union['Element', None]:
        return self.__related('nextElementSibling')

    @property
    @_exists
    @_ignore_window_document
    def previous(self) -> Union['Element', None]:
        return self.__related('previousElementSibling')

    def __related(self, js_property: str) -> Union['Element', None]:
        """Return the element that the given JS property of this element refers to, if any."""
        node_id = self._window.evaluate_js(
            f"""
            {self._query_command};
            var related = element.{js_property};
            related ? pywebview._getNodeId(related) : null
        """
        )
        return Element(self._window, node_id) if node_id else None

    @_exists
    @_ignore_window_document
    def hide(self) -> None:
        self.__original_display = self._window.evaluate_js(
            f'{self._query_command}; element.style.display'
        )
        self._window.run_js(f"{self._query_command}; element.style.display = 'none'")

    @_exists
    @_ignore_window_document
    def show(self) -> None:
        current_display = self._window.evaluate_js(f'{self._query_command}; element.style.display')

        if current_display == 'none':
            display = self.__original_display or 'block'
            self._window.run_js(f"{self._query_command}; element.style.display = '{display}'")

    @_exists
    @_ignore_window_document
    def toggle(self) -> None:
        current_display = self._window.evaluate_js(f'{self._query_command}; element.style.display')

        if current_display == 'none':
            self.show()
        else:
            self.hide()

    @_exists
    @_ignore_window_document
    def append(self, html: str, mode: ManipulationMode = ManipulationMode.LastChild) -> 'Element':
        return self._window.dom.create_element(html, self, mode)

    @_exists
    @_ignore_window_document
    def empty(self) -> None:
        self._window.run_js(f"{self._query_command}; element.innerHTML = ''")

    @_exists
    @_ignore_window_document
    def remove(self) -> None:
        self._share_listeners()
        self._window.run_js(f'{self._query_command}; element.remove()')

        if self._node_id in self._window.dom._elements:
            self._window.dom._elements.pop(self._node_id)

        handler_ids = json.dumps(list(self._event_listeners))
        self._window.run_js(
            f"""
            {handler_ids}.forEach(function(handlerId) {{
                delete pywebview._eventHandlers[handlerId]
            }})
        """
        )
        self._event_listeners.clear()
        self._event_handlers.clear()
        self._exists = False

    @_exists
    @_ignore_window_document
    def copy(
        self,
        target: Union[str, 'Element', None] = None,
        mode: ManipulationMode = ManipulationMode.LastChild,
        id: str | None = None,
    ) -> 'Element':
        resolved_target: Element | None
        if isinstance(target, str):
            resolved_target = self._window.dom.get_element(target)
        elif target is None:
            resolved_target = self.parent
        else:
            resolved_target = target

        if resolved_target is None:
            raise WebViewException('Unable to resolve copy target element')

        if id:
            id_command = f'newElement.id = {json.dumps(id)}'
        else:
            id_command = 'newElement.removeAttribute("id")'

        node_id = self._window.evaluate_js(
            f"""
            {self._query_command};
            var target = document.querySelector('[data-pywebview-id=\"{resolved_target._node_id}\"]');
            var newElement = element.cloneNode(true);
            newElement.removeAttribute('data-pywebview-id');
            {id_command};

            var nodeId = pywebview._getNodeId(newElement);
            pywebview._insertNode(newElement, target, '{mode.value}')
            nodeId;
        """
        )

        self._share_listeners()
        new_element = Element(self._window, node_id)
        for event, handlers in list(self._event_handlers.items()):
            for handler in handlers:
                new_element.on(event, handler)

        return new_element

    @_exists
    @_ignore_window_document
    def move(
        self, target: Union[str, 'Element'], mode: ManipulationMode = ManipulationMode.LastChild
    ) -> 'Element':
        resolved_target = (
            self._window.dom.get_element(target) if isinstance(target, str) else target
        )

        if resolved_target is None:
            raise WebViewException('Unable to resolve move target element')

        self._window.run_js(
            f"""
            {self._query_command};
            var target = document.querySelector('[data-pywebview-id=\"{resolved_target._node_id}\"]');
            pywebview._insertNode(element, target, '{mode.value}')
        """
        )
        return self

    def _share_listeners(self) -> None:
        """Use the listeners of the element registered for this node, as get_element returns a
        new wrapper on every call and the bridge dispatches to the registered one."""
        owner = self._window.dom._elements.get(self._node_id)
        if owner is not None and owner is not self:
            self._event_handlers = owner._event_handlers
            self._event_listeners = owner._event_listeners

    @_exists
    def on(self, event: str, callback: Callable | DOMEventHandler) -> None:
        if self._node_id not in self._window.dom._elements:
            self._window.dom._elements[self._node_id] = self
        self._share_listeners()

        if isinstance(callback, DOMEventHandler):
            prevent_default = 'e.preventDefault();' if callback.prevent_default else ''
            stop_propagation = 'e.stopPropagation();' if callback.stop_propagation else ''
            if callback.stop_immediate_propagation:
                stop_propagation += 'e.stopImmediatePropagation();'
            debounce = callback.debounce
            callback = callback.callback
        else:
            prevent_default = ''
            stop_propagation = ''
            debounce = 0

        # the bridge dispatches each event only to the handler of the listener that fired
        handler_id = secrets.token_hex(8)
        callback_func = f"function(e) {{ window.pywebview._jsApiCallback('pywebviewEventHandler', {{ event: e, nodeId: '{self._node_id}', handlerId: '{handler_id}' }}, 'eventHandler') }}"
        if debounce > 0:
            callback_func = f'pywebview._debounce({callback_func}, {debounce})'

        registered = self._window.evaluate_js(
            f"""
            {self._query_command};
            var handlerId = '{handler_id}';

            if (element) {{
                // the script runs at page scope, so bind the callback per listener
                pywebview._eventHandlers[handlerId] = (function(callback) {{
                    return function(e) {{
                        {prevent_default}
                        {stop_propagation}
                        callback(e);
                    }}
                }})({callback_func});

                element.addEventListener('{escape_string(event)}', pywebview._eventHandlers[handlerId]);
            }};
            !!element;
        """
        )

        if registered:
            self._event_handlers[event].append(callback)
            self._event_listeners[handler_id] = (event, callback)

        if event == 'drop':
            _dnd_state['num_listeners'] += 1

    @_exists
    def off(self, event: str, callback: Callable) -> None:
        self._share_listeners()
        # remove the most recently registered listener for this callback
        handler_id = next(
            (
                listener_id
                for listener_id, listener in reversed(self._event_listeners.items())
                if listener == (event, callback)
            ),
            None,
        )

        if not handler_id:
            return

        self._window.run_js(
            f"""
            {self._query_command};
            var callback = pywebview._eventHandlers['{handler_id}'];
            if (element) {{
                element.removeEventListener('{escape_string(event)}', callback);
                delete pywebview._eventHandlers['{handler_id}'];
            }}
        """
        )

        del self._event_listeners[handler_id]
        self._event_handlers[event].remove(callback)

        if not self._event_listeners:
            self._window.dom._elements.pop(self._node_id, None)

        if event == 'drop':
            _dnd_state['num_listeners'] = max(0, _dnd_state['num_listeners'] - 1)

    @_exists
    def __generate_events(self):
        from webview.dom.event import DOMEvent

        events = self._window.evaluate_js(
            f"""
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
        """
        )

        for event in events:
            setattr(self.events, event, DOMEvent(event, self))

    @_exists
    def __str__(self) -> str:
        return repr(self)

    @_exists
    def __repr__(self) -> str:
        if self._node_id in ('document', 'window'):
            return self._node_id
        return self.node['outerHTML']

    @_exists
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Element) and self._node_id == other._node_id
