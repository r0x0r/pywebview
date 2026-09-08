import webview


def test_screens():
    assert len(webview.screens) > 0
    assert webview.screens[0].width > 0
    assert webview.screens[0].height > 0
    assert isinstance(webview.screens[0].x, int)
    assert isinstance(webview.screens[0].y, int)


def test_screen_scale():
    """Test that screens have a scale property."""
    screens = webview.screens
    assert len(screens) > 0

    for screen in screens:
        # Scale should be a float
        assert isinstance(screen.scale, float)
        # Scale should be positive
        assert screen.scale > 0
        # Scale should be reasonable (between 0.5 and 4.0 for most displays)
        assert 0.5 <= screen.scale <= 4.0


def test_screen_physical_pixels():
    """Test physical pixel properties."""
    screens = webview.screens
    assert len(screens) > 0

    screen = screens[0]

    # Physical pixels should be logical pixels * scale
    assert screen.physical_x == int(screen.x * screen.scale)
    assert screen.physical_y == int(screen.y * screen.scale)
    assert screen.physical_width == int(screen.width * screen.scale)
    assert screen.physical_height == int(screen.height * screen.scale)

    # Physical dimensions should be integers
    assert isinstance(screen.physical_x, int)
    assert isinstance(screen.physical_y, int)
    assert isinstance(screen.physical_width, int)
    assert isinstance(screen.physical_height, int)

    # Physical dimensions should be positive (or zero for coordinates)
    assert screen.physical_width > 0
    assert screen.physical_height > 0


def test_screen_dpi():
    """Test DPI calculation."""
    screens = webview.screens
    assert len(screens) > 0

    for screen in screens:
        # DPI should be scale * 96
        assert screen.dpi == int(screen.scale * 96)
        # DPI should be an integer
        assert isinstance(screen.dpi, int)
        # DPI should be reasonable (48-384 for most displays)
        assert 48 <= screen.dpi <= 384


def test_screen_repr():
    """Test screen string representation."""
    screens = webview.screens
    assert len(screens) > 0

    screen = screens[0]
    repr_str = repr(screen)

    # Should contain dimensions
    assert str(screen.width) in repr_str
    assert str(screen.height) in repr_str

    # Should contain coordinates
    assert str(screen.x) in repr_str
    assert str(screen.y) in repr_str

    # If scale != 1.0, should show scale
    if screen.scale != 1.0:
        assert 'x' in repr_str  # scale shown as "2.00x" format


def test_screen_manual_creation():
    """Test creating Screen objects manually with different scales."""
    from webview.screen import Screen

    # Test with scale = 1.0 (default)
    screen1 = Screen(0, 0, 1920, 1080)
    assert screen1.scale == 1.0
    assert screen1.physical_width == 1920
    assert screen1.physical_height == 1080
    assert screen1.dpi == 96

    # Test with scale = 2.0 (Retina/HiDPI)
    screen2 = Screen(0, 0, 1920, 1080, scale=2.0)
    assert screen2.scale == 2.0
    assert screen2.physical_width == 3840
    assert screen2.physical_height == 2160
    assert screen2.dpi == 192

    # Test with scale = 1.5 (150% scaling)
    screen3 = Screen(100, 200, 1920, 1080, scale=1.5)
    assert screen3.scale == 1.5
    assert screen3.physical_x == 150
    assert screen3.physical_y == 300
    assert screen3.physical_width == 2880
    assert screen3.physical_height == 1620
    assert screen3.dpi == 144


def test_screen_origin_scale():
    """
    origin_scale lets a screen's position convert with a different factor
    than its size — used on mixed-DPI Windows/WinUI3 setups where every
    screen's origin shares one desktop-wide scale (so screens don't
    overlap) while each screen's own scale is still right for its size.
    """
    from webview.screen import Screen

    # Omitted: defaults to `scale`, preserving the plain x * scale contract
    # every other backend relies on.
    screen = Screen(100, 200, 1920, 1080, scale=1.5)
    assert screen.origin_scale == screen.scale == 1.5
    assert screen.physical_x == 150
    assert screen.physical_y == 300

    # A 200%-scaled secondary monitor at physical x=1920 next to a 100%
    # primary: get_screens() reports it at logical x=1920 (physical /
    # the shared primary scale), not logical x=960 (physical / its own
    # scale), so it doesn't overlap the primary. physical_x must still
    # recover the true physical origin, 1920 - not 3840 (1920 * 2.0).
    mixed = Screen(1920, 0, 1920, 1080, scale=2.0, origin_scale=1.0)
    assert mixed.scale == 2.0
    assert mixed.origin_scale == 1.0
    assert mixed.physical_x == 1920
    assert mixed.physical_width == 3840
