import webview


def test_default_drag_region_selector_keeps_upstream_compatibility():
    assert webview.settings['DRAG_REGION_SELECTOR'] == '.pywebview-drag-region'
