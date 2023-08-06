class Screen:
    def __init__(self, width: int, height: int, frame: object = None) -> None:
        self.width = int(width)
        self.height = int(height)
        self.frame = frame

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return '(%s, %s)' % (self.width, self.height)
