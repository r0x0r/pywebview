from typing import Any
from webview.element import Element


class DOM:
    def __init__(self, window):
        self.__window = window
        self._elements = {}

    @property
    def document(self) -> Any:
        document = self.__window.evaluate_js('document')
        document['_pywebviewId'] = 'document'
        element = Element(self.__window, document)

        if 'document' not in self._elements:
            self._elements['document'] = element

        return element

    @property
    def window(self) -> Any:
        window = self.__window.evaluate_js('pywebview.domJSON.toJSON(window, {deep: false, metadata: false})')
        window['_pywebviewId'] = 'window'
        element = Element(self.__window, window)

        if 'window' not in self._elements:
            self._elements['window'] = element

        return element

