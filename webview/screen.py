class Screen:
    def __init__(
        self, x: int, y: int, width: int, height: int, frame: object = None, scale: float = 1.0
    ) -> None:
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.frame = frame
        self.scale = float(scale)

    @property
    def physical_x(self) -> int:
        """X coordinate in physical pixels."""
        return int(self.x * self.scale)

    @property
    def physical_y(self) -> int:
        """Y coordinate in physical pixels."""
        return int(self.y * self.scale)

    @property
    def physical_width(self) -> int:
        """Width in physical pixels."""
        return int(self.width * self.scale)

    @property
    def physical_height(self) -> int:
        """Height in physical pixels."""
        return int(self.height * self.scale)

    @property
    def dpi(self) -> int:
        """DPI (dots per inch) for this screen."""
        return int(self.scale * 96)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        scale_str = f' {self.scale:.2f}x' if self.scale != 1.0 else ''
        return f'{self.width}x{self.height} at {self.x},{self.y}{scale_str}'
