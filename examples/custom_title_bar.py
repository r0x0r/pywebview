"""Custom title bar example for pywebview on Windows (WinUI 3 backend).

Replaces the system chrome title bar with a custom XAML element injected
via the ``before_show`` event.

Reference: https://learn.microsoft.com/en-us/windows/apps/develop/title-bar

Works on Windows only (WinUI 3 backend).
"""

import webview

_TITLE_BAR_XAML = """\
<Grid
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    Name="TitleBar">
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
# Height is Auto here and updated to the exact logical height in on_loaded.
_TITLE_ROW_XAML = (
    '<RowDefinition'
    ' xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"'
    ' Height="Auto"/>'
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
    #    b) Set the button height to match title_bar.height at current DPI.
    def on_loaded(sender, _args):
        tb = sender.as_(Grid)
        scale = tb.xaml_root.rasterization_scale

        # Round to the nearest integer logical pixel so all elements sit on
        # exact pixel boundaries — prevents blurry text and icons.
        logical_height = round(win.app_window.title_bar.height / scale)
        tb.height = logical_height
        root.row_definitions[0].height = GridLength(logical_height, GridUnitType.PIXEL)

        tb.column_definitions[0].width = GridLength(
            round(win.app_window.title_bar.left_inset / scale), GridUnitType.PIXEL
        )
        tb.column_definitions[3].width = GridLength(
            round(win.app_window.title_bar.right_inset / scale), GridUnitType.PIXEL
        )

        fullscreen_button.height = logical_height

    fullscreen_button = title_bar.find_name('FullscreenButton')
    fullscreen_button = fullscreen_button.as_(Button)
    fullscreen_button.add_click(lambda _s, _e: window.toggle_fullscreen())
    title_bar.add_loaded(on_loaded)


if __name__ == '__main__':
    window = webview.create_window(
        'Custom title bar',
        html=_HTML_CONTENT,
    )

    window.events.before_show += on_before_show

    webview.start(gui='winui3')
