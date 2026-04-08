"""Custom title bar example for pywebview on Windows (WinUI 3 backend).

Replaces the system chrome title bar with a custom XAML element injected
via the ``before_show`` event.

Reference: https://learn.microsoft.com/en-us/windows/apps/develop/title-bar

Works on Windows only (WinUI 3 backend).
"""

import webview

_TITLE_BAR_HEIGHT = 48

# The Grid named "TitleBar" is registered as the draggable caption region.
# Columns 0 and 3 are padding stubs; their widths are set in the Loaded
# handler to match AppWindowTitleBar.LeftInset / RightInset so that the
# custom button aligns exactly with the system caption buttons (min/max/close).
_TITLE_BAR_XAML = f"""\
<Grid
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    Name="TitleBar"
    Height="{_TITLE_BAR_HEIGHT}">
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="0"/>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="Auto"/>
        <ColumnDefinition Width="0"/>
    </Grid.ColumnDefinitions>
    <TextBlock
        Grid.Column="1"
        Text="pywebview — Custom Title Bar"
        VerticalAlignment="Center"
        Margin="16,0,0,0"/>
    <Button
        Name="FullscreenButton"
        Grid.Column="2"
        VerticalAlignment="Top"
        Width="46"
        Padding="0"
        CornerRadius="0">
        <Button.Resources>
            <SolidColorBrush x:Key="ButtonBackground"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Color="Transparent"/>
            <SolidColorBrush x:Key="ButtonBackgroundPointerOver"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Color="#19000000"/>
            <SolidColorBrush x:Key="ButtonBackgroundPressed"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Color="#33000000"/>
            <SolidColorBrush x:Key="ButtonBorderBrush"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Color="Transparent"/>
            <SolidColorBrush x:Key="ButtonBorderBrushPointerOver"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Color="Transparent"/>
            <SolidColorBrush x:Key="ButtonBorderBrushPressed"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Color="Transparent"/>
        </Button.Resources>
        <FontIcon Glyph="&#xE740;" FontSize="10"/>
    </Button>
</Grid>
"""

# Inline XAML for the extra RowDefinition that holds the title bar.
_TITLE_ROW_XAML = (
    '<RowDefinition'
    ' xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"'
    f' Height="{_TITLE_BAR_HEIGHT}"/>'
)

_HTML_CONTENT = """\
<!DOCTYPE html>
<html>
<head>
    <title>Custom Title Bar</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
    </style>
</head>
<body>
    <h1>Custom Title Bar Example</h1>
    <p>This window has a custom title bar built with XAML.</p>
    <p>Click the fullscreen button in the title bar to toggle fullscreen mode.</p>
</body>
</html>
"""


def on_before_show(window):
    """Inject a custom XAML title bar before the native window is shown.

    ``window.native`` is the underlying WinUI 3 ``Window``.
    """
    from winui3.microsoft.ui.xaml import GridLength, GridUnitType
    from winui3.microsoft.ui.xaml.controls import Button, Grid, RowDefinition
    from winui3.microsoft.ui.xaml.markup import XamlReader

    win = window.native

    # 1. Remove the OS chrome strip so XAML content fills the full height.
    win.extends_content_into_title_bar = True

    # 2. Insert a new fixed-height row at the top of the root Grid.
    #    The root Grid created by pywebview has:
    #      Row 0 – Auto  – MenuBar  (collapsed by default)
    #      Row 1 – *     – WebView2
    #    After insert_at(0, …) those become rows 1 and 2.
    root = win.content.as_(Grid)
    title_row = XamlReader.load(_TITLE_ROW_XAML).as_(RowDefinition)
    root.row_definitions.insert_at(0, title_row)

    # Shift every existing child down one row.
    for child in root.children:
        Grid.set_row(child, Grid.get_row(child) + 1)

    # 3. Build the title bar, place it in row 0, and add it to the tree.
    title_bar = XamlReader.load(_TITLE_BAR_XAML).as_(Grid)
    Grid.set_row(title_bar, 0)
    Grid.set_column_span(title_bar, 2)
    root.children.append(title_bar)

    # 4. Register the element as the drag / caption region AFTER it is in
    #    the visual tree (required by WinUI 3).
    win.set_title_bar(title_bar)

    # 5. After the first layout pass:
    #    a) Set the left/right padding columns to match the system caption
    #       button insets so the custom button sits flush against them.
    #    b) Set the but,ton height to match title_bar.height at current DPI.
    #    c) Register the button's bounding rect as a Passthrough region via
    #       InputNonClientPointerSource so that single clicks are delivered
    #       to the button instead of being swallowed by drag detection.
    def on_loaded(sender, _args):
        tb = sender.as_(Grid)
        scale = tb.xaml_root.rasterization_scale

        tb.column_definitions[0].width = GridLength(
            win.app_window.title_bar.left_inset / scale, GridUnitType.PIXEL
        )
        tb.column_definitions[3].width = GridLength(
            win.app_window.title_bar.right_inset / scale, GridUnitType.PIXEL
        )

        button = tb.find_name('FullscreenButton')
        if button:
            button = button.as_(Button)
            button.height = win.app_window.title_bar.height / scale
            try:
                from winrt.windows.graphics import RectInt32
                from winui3.microsoft.ui.input import (
                    InputNonClientPointerSource,
                    NonClientRegionKind,
                )

                transform = button.transform_to_visual(None)
                origin = transform.transform_point((0.0, 0.0))
                rect = RectInt32(
                    int(origin.x * scale),
                    int(origin.y * scale),
                    int(button.actual_width * scale),
                    int(button.actual_height * scale),
                )
                source = InputNonClientPointerSource.get_for_window_id(win.app_window.id)
                source.set_region_rects(NonClientRegionKind.PASSTHROUGH, [rect])
            except (ImportError, AttributeError):
                pass  # passthrough region not available in this winui3 version

    title_bar.add_loaded(on_loaded)

    # 6. Wire up the Fullscreen button.
    fullscreen_button = title_bar.find_name('FullscreenButton')
    if fullscreen_button:
        fullscreen_button.as_(Button).add_click(lambda _s, _e: window.toggle_fullscreen())


if __name__ == '__main__':
    window = webview.create_window(
        'Custom title bar',
        html=_HTML_CONTENT,
    )

    window.events.before_show += on_before_show

    webview.start(gui='winui3')
