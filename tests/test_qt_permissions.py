"""Exercise Qt's native permission-policy argument without opening a window."""

import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('PYWEBVIEW_GUI') != 'qt', reason='Qt backend only')


def test_qt_permission_policies():
    from qtpy.QtCore import QCoreApplication, QEvent, QUrl

    from webview.platforms import qt

    if not qt.is_webengine:
        pytest.skip('QtWebEngine only')

    app = qt.QApplication.instance() or qt.QApplication(['permission-test'])
    calls = []

    class Page(qt.QWebPage):
        onFeaturePermissionRequested = qt.BrowserView.WebPage.onFeaturePermissionRequested

        def setFeaturePermission(self, origin, feature, policy):
            # Call the real binding: PyQt6 rejects int policies here.
            super().setFeaturePermission(origin, feature, policy)
            calls.append((origin, feature, policy))

    page = Page()
    page.featurePermissionRequested.connect(page.onFeaturePermissionRequested)
    origin = QUrl('https://example.invalid')
    granted = qt.QWebPage.PermissionPolicy.PermissionGrantedByUser
    denied = qt.QWebPage.PermissionPolicy.PermissionDeniedByUser
    allowed = {
        qt.QWebPage.Feature.MediaAudioCapture,
        qt.QWebPage.Feature.MediaVideoCapture,
        qt.QWebPage.Feature.MediaAudioVideoCapture,
    }
    features = [*allowed, qt.QWebPage.Feature.Geolocation, qt.QWebPage.Feature.Notifications]
    clipboard = getattr(qt.QWebPage.Feature, 'ClipboardReadWrite', None)
    if clipboard is not None:
        features.append(clipboard)

    for feature in features:
        page.onFeaturePermissionRequested(origin, feature)
        assert calls[-1] == (origin, feature, granted if feature in allowed else denied)
        page.featurePermissionRequested.emit(origin, feature)
        assert calls[-1] == (origin, feature, granted if feature in allowed else denied)

    assert len(calls) == 2 * len(features)
    page.deleteLater()
    QCoreApplication.sendPostedEvents(page, QEvent.DeferredDelete)
    app.processEvents()
