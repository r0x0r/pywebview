class ClassList:
    def __init__(self, element, classes=None):
        self.__element = element

        if classes:
            classes = ' '.join(classes)
            self.__element._window.evaluate_js(f"{self.__element._query_command}; element.className = '{classes}'")

    def append(self, cls):
        self.__element._window.run_js(f"{self.__element._query_command}; element.classList.add('{cls}')")

    def remove(self, cls):
        self.__element._window.run_js(f"{self.__element._query_command}; element.classList.remove('{cls}')")

    def toggle(self, cls):
        self.__element._window.run_js(f"{self.__element._query_command}; element.classList.toggle('{cls}')")

    def __get_classes(self):
        classes = self.__element._window.evaluate_js(f"{self.__element._query_command}; element.className").split(' ')
        return [c for c in classes if c != '']

    def __getitem__(self, index):
        classes = self.__get_classes()
        return classes[index]

    def __len__(self):
        classes = self.__get_classes()
        return len(classes)

    def __str__(self):
        classes = self.__get_classes()
        return str(classes)

    def __repr__(self):
        classes = self.__get_classes()
        return repr(classes)

    def clear(self):
        self.__element._window.run_js(f"{self.__element._query_command}; element.className = ''")
