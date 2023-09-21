from typing import Optional
from webview.dom.element import Element
from webview.util import escape_quotes


class DOM:
    def __init__(self, window):
        self.__window = window
        window.events.loaded += self.__on_loaded
        self._elements = {}

    def __on_loaded(self):
        self._elements = {}

    @property
    def body(self) -> Element:
        return Element(self.__window, 'body')

    @property
    def document(self) -> Element:
        return Element(self.__window, 'document')

    @property
    def window(self) -> Element:
        return Element(self.__window, 'window')

    def create_element(self, html: str, parent: Optional[Element]=None) -> Element:
        self.__window.events.loaded.wait()
        parent_command = parent._query_command if parent else 'var element = document.body'
        node_id = self.__window.evaluate_js(f"""
            {parent_command};
            var template = document.createElement('template');
            template.innerHTML = '{escape_quotes(html)}'.trim();
            var child = template.content.firstChild;
            element.appendChild(child);
            pywebview._getNodeId(child);
        """)

        return Element(self.__window, node_id)

    def get_element(self, selector: str) -> Optional[Element]:
        self.__window.events.loaded.wait()
        node_id = self.__window.evaluate_js(f"""
            var element = document.querySelector('{selector}');
            pywebview._getNodeId(element);
        """)

        return Element(self.__window, node_id) if node_id else None

    def get_elements(self, selector: str) -> list[Element]:
        self.__window.events.loaded.wait()
        code = f"""
            var elements = document.querySelectorAll('{selector}');
            nodeIds = [];
            for (var i = 0; i < elements.length; i++) {{
                var nodeId = pywebview._getNodeId(elements[i]);
                nodeIds.push(nodeId);
            }}

            nodeIds
        """

        node_ids = self.__window.evaluate_js(code)
        return [Element(self.__window, node_id) for node_id in node_ids]




