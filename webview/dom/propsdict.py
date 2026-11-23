from __future__ import annotations

import json
from enum import Enum
from typing import Any

from webview.util import css_to_camel, escape_string


class DOMPropType(Enum):
    Style = 1
    Attribute = 2


class PropsDict:
    def __init__(self, element, type: DOMPropType, props: dict[str, Any] | None = None):
        self.__element = element
        self.__type = type
        # Value that removes a property
        self.__empty = '' if type == DOMPropType.Style else None

        if props:
            self.update(props)

    def __getitem__(self, key: str) -> Any:
        return self.__get_data().get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.update({key: value})

    def __delitem__(self, key: str) -> None:
        self.update({key: self.__empty})

    def __contains__(self, key: str) -> bool:
        return key in self.__get_data()

    def keys(self) -> Any:
        return self.__get_data().keys()

    def values(self) -> Any:
        return self.__get_data().values()

    def items(self) -> Any:
        return self.__get_data().items()

    def get(self, key: str, default: Any = None) -> Any:
        return self.__get_data().get(key, default)

    def clear(self) -> None:
        self.update(dict.fromkeys(self.__get_data(), self.__empty))

    def copy(self) -> dict[str, Any]:
        return self.__get_data()

    def update(self, other_dict: dict[str, str | int | float | None]) -> None:
        if self.__type == DOMPropType.Style:
            self.__set_style(other_dict)
        else:
            self.__set_attributes(other_dict)

    def pop(self, key: str, default: Any = None) -> Any:
        return self.__get_data().pop(key, default)

    def popitem(self) -> tuple[str, Any]:
        return self.__get_data().popitem()

    def __str__(self) -> str:
        return str(self.__get_data())

    def __repr__(self) -> str:
        return repr(self.__get_data())

    def __get_data(self) -> dict[str, Any]:
        if self.__type == DOMPropType.Style:
            return self.__get_style()
        return self.__get_attributes()

    def __get_attributes(self) -> dict[str, Any]:
        return self.__element._window.evaluate_js(
            f"""
            {self.__element._query_command};
            var attributes = element.attributes;
            var result = {{}};
            for (var i = 0; i < attributes.length; i++) {{
                if (attributes[i].name === 'data-pywebview-id') {{
                    continue;
                }}
                result[attributes[i].name] = attributes[i].value;
            }}
            result
        """
        )

    def __set_attributes(self, props: dict[str, Any]) -> None:
        # The internal ID is skipped in any case, as setAttribute lowercases names on HTML elements
        self.__element._window.evaluate_js(
            f"""
            {self.__element._query_command};
            var values = JSON.parse('{escape_string(json.dumps(props))}');

            for (var key in values) {{
                var value = values[key];
                if (key.toLowerCase() === 'data-pywebview-id') {{
                    continue;
                }} else if (value === null || value === undefined) {{
                    element.removeAttribute(key);
                }} else {{
                    element.setAttribute(key, value);
                }}
            }}
        """
        )

    def __get_style(self) -> dict[str, Any]:
        return self.__element._window.evaluate_js(
            f"""
            {self.__element._query_command};
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
        """
        )

    def __set_style(self, style: dict[str, Any]) -> None:
        converted_style = json.dumps({css_to_camel(key): value for key, value in style.items()})
        self.__element._window.evaluate_js(
            f"""
            {self.__element._query_command};
            var styles = JSON.parse('{escape_string(converted_style)}');

            for (var key in styles) {{
                element.style[key] = styles[key];
            }}
        """
        )
