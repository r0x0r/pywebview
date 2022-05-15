class Menu:
    def __init__(self, title, items=[]):
        """
        Args:
            title: the menu or submenu title
            items: the contents of the menu (can consist of Menu, MenuAction, or MenuSeparator instances)
        """
        self.title = title
        self.items = items

class MenuAction:
    def __init__(self, title, function, shortcut=None):
        self.title = title
        self.function = function
        # TODO: support platform-agnostic shortcut
        # self.shortcut = shortcut

class MenuSeparator:
    pass
