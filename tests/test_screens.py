import webview


def test_screens():
    assert len(webview.screens) > 0
    assert webview.screens[0].width > 0
    assert webview.screens[0].height > 0
    assert type(webview.screens[0].x) == int
    assert type(webview.screens[0].y) == int
