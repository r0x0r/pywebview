class Screen:
    def __init__(self, x: int, y: int, width: int, height: int, frame: object = None) -> None:
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.frame = frame

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f'{self.width}x{self.height} at {self.x},{self.y}'
