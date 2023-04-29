class Screen:
    def __init__(self, width: int, height: int) -> None:
        self.width = int(width)
        self.height = int(height)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return '(%s, %s)' % (self.width, self.height)
