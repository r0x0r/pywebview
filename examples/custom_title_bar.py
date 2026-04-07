"""Custom title bar example for pywebview on Windows (WinUI 3 backend).

Replaces the system chrome title bar with a custom XAML element injected
via the ``before_show`` event. Serves a local HTML page with a fullscreen
toggle button.

The element is registered with ``Window.set_title_bar()`` so that dragging
it moves the window.

Reference: https://learn.microsoft.com/en-us/windows/apps/develop/title-bar

Works on Windows only (WinUI 3 backend).
"""

import webview

_TITLE_BAR_HEIGHT = 48

# The Grid named "TitleBar" will be registered as the draggable caption area.
_TITLE_BAR_XAML = f"""\
<Grid
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    Name="TitleBar"
    Height="{_TITLE_BAR_HEIGHT}">
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="Auto"/>
    </Grid.ColumnDefinitions>
    <TextBlock
        Grid.Column="0"
        Text="pywebview — Custom Title Bar"
        VerticalAlignment="Center"
        Margin="16,0,0,0"/>
    <Button
        Name="FullscreenButton"
        Grid.Column="1"
        Content="Fullscreen"
        VerticalAlignment="Center"
        Margin="0,0,8,0"
        Padding="8,4"/>
</Grid>
"""

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
    <p>Click the "Fullscreen" button in the title bar to toggle fullscreen mode.</p>
</body>
</html>
"""


def on_before_show(window):
    """Inject a custom XAML title bar before the native window is shown.

    ``window.native`` is pywebview's ``BrowserForm`` (the WinUI 3 wrapper).
    Its ``window`` attribute is the underlying WinUI 3 ``Window``, which
    exposes ``app_window`` (``AppWindow``) for lower-level customisation.
    """
    from winui3.microsoft.ui.xaml.controls import Grid
    from winui3.microsoft.ui.xaml.markup import XamlReader

    win = window.native  # BrowserForm

    # Extend the client area into the OS title bar strip so our XAML fills
    # the full window height and the system chrome band disappears.
    win.extends_content_into_title_bar = True

    # Build the custom title bar element from inline XAML and register it
    # as the draggable caption / drag handle.
    title_bar = XamlReader.load(_TITLE_BAR_XAML).as_(Grid)
    win.set_title_bar(title_bar)

    # Get the fullscreen button and attach a click handler
    fullscreen_button = title_bar.find_name('FullscreenButton')
    if fullscreen_button:
        fullscreen_button.click += lambda sender, args: window.toggle_fullscreen()


if __name__ == '__main__':
    window = webview.create_window(
        'Custom title bar',
        html=_HTML_CONTENT,
    )

    window.events.before_show += on_before_show

    webview.start()
