class Screen:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f'({self.width}, {self.height})'
