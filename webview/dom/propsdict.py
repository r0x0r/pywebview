import json
from enum import Enum
from typing import Any, Dict, Optional, Union
from webview.util import css_to_camel, escape_quotes


class DOMPropType(Enum):
    Style = 1
    Attribute = 2


class PropsDict:
    def __init__(self, element, type: DOMPropType, props: Optional[Dict[str, Any]] = None):
        self.__element = element
        self.__type = type

        if not props:
            return

        if type == DOMPropType.Style:
            converted_style = json.dumps({css_to_camel(key): value for key, value in props.items()})
            self.__element._window.evaluate_js(f"""
                {self.__element._query_command};
                var styles = JSON.parse('{converted_style}');

                for (var key in styles) {{
                    element.style[key] = styles[key];
                }}
            """)

        elif type == DOMPropType.Attribute:
            converted_attributes = json.dumps({
                escape_quotes(key): escape_quotes(value) for key, value in props.items()
            })

            self.__element._window.evaluate_js(f"""
                {self.__element._query_command};
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

    def __getitem__(self, key):
        data = self.__get_data()
        return data.get(key)

    def __setitem__(self, key, value):
        if self.__type == DOMPropType.Style:
            self.__set_style({key: value})
        elif self.__type == DOMPropType.Attribute:
            self.__set_attribute({key: value})

    def __delitem__(self, key):
        if self.__type == DOMPropType.Style:
            self.__set_style({key: ''})
        elif self.__type == DOMPropType.Attribute:
            self.__set_attribute({key: None})

    def __contains__(self, key):
        data = self.__get_data()
        return key in data

    def keys(self):
        data = self.__get_data()
        return data.keys()

    def values(self):
        data = self.__get_data()
        return data.values()

    def items(self):
        data = self.__get_data()
        return data.items()

    def get(self, key, default=None):
        data = self.__get_data()
        return data.get(key, default)

    def clear(self):
        data = self.__get_data()

        for key in data.keys():
            data[key] = '' if self.__type == DOMPropType.Style else None

        if self.__type == DOMPropType.Style:
            self.__set_style(data)
        elif self.__type == DOMPropType.Attribute:
            self.__set_attribute(data)

    def copy(self):
        return self.__get_data()

    def update(self, other_dict: Dict[str, Union[str, int, float, None]]):
        if self.__type == DOMPropType.Style:
            self.__set_style(other_dict)
        elif self.__type == DOMPropType.Attribute:
            self.__set_attribute(other_dict)

    def pop(self, key, default=None):
        data = self.__get_data()
        return data.pop(key, default)

    def popitem(self):
        data = self.__get_data()
        return data.popitem()

    def __str__(self):
        data = self.__get_data()
        return str(data)

    def __repr__(self):
        data = self.__get_data()
        return repr(data)

    def __get_data(self) -> Dict[str, Any]:
        if self.__type == DOMPropType.Style:
            return self.__get_style()
        elif self.__type == DOMPropType.Attribute:
            return self.__get_attributes()

    def __get_attributes(self) -> Dict[str, Any]:
        return self.__element._window.evaluate_js(f"""
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
        """)

    def __set_attribute(self, props: Dict[str, Any]):
        self.__element._window.evaluate_js(f"""
            {self.__element._query_command};
            var values = JSON.parse('{json.dumps(props)}');

            for (var key in values) {{
                var value = values[key];
                if (value === null || value === undefined) {{
                    element.removeAttribute(key);
                }} else {{
                    element.setAttribute(key, value);
                }}
            }}
        """)

    def __get_style(self) -> Dict[str, Any]:
        return self.__element._window.evaluate_js(f"""
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
        """)

    def __set_style(self, style: Dict[str, Any]):
        converted_style = json.dumps({css_to_camel(key): value for key, value in style.items()})
        self.__element._window.evaluate_js(f"""
            {self.__element._query_command};
            var styles = JSON.parse('{converted_style}');

            for (var key in styles) {{
                var value = styles[key];
                element.style[key] = value;
            }}
        """)