class Screen:
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        frame: object = None,
        scale: float = 1.0,
        origin_scale: float | None = None,
    ) -> None:
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.frame = frame
        self.scale = float(scale)
        # `scale` is this monitor's own true DPI scale (used for `.dpi`).
        # `origin_scale` is the scale this Screen's own x/y/width/height
        # were actually computed with, and is what physical_x/y/width/height
        # must use to round-trip correctly. These differ on backends where
        # reporting a monitor's true geometry requires a single desktop-wide
        # coordinate space shared by every screen (see WinUI3's
        # get_screens(): every screen's x/y/width/height are computed via
        # the primary monitor's scale so mixed-DPI screens tile without
        # overlap - "own scale for size" alone isn't enough because a
        # lower-DPI monitor adjacent to a higher-DPI one can still overlap
        # it otherwise). Defaults to `scale` so every other backend's
        # single-scale-per-monitor model is unaffected.
        self.origin_scale = float(origin_scale) if origin_scale is not None else self.scale

    @property
    def physical_x(self) -> int:
        """X coordinate in physical pixels."""
        return int(self.x * self.origin_scale)

    @property
    def physical_y(self) -> int:
        """Y coordinate in physical pixels."""
        return int(self.y * self.origin_scale)

    @property
    def physical_width(self) -> int:
        """Width in physical pixels."""
        return int(self.width * self.origin_scale)

    @property
    def physical_height(self) -> int:
        """Height in physical pixels."""
        return int(self.height * self.origin_scale)

    @property
    def dpi(self) -> int:
        """DPI (dots per inch) for this screen."""
        return int(self.scale * 96)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        scale_str = f' {self.scale:.2f}x' if self.scale != 1.0 else ''
        return f'{self.width}x{self.height} at {self.x},{self.y}{scale_str}'
