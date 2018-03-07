import threading
from .util import run_test, destroy_window


def evaluate_js():
    import webview

    def _evaluate_js(webview):
        result = webview.evaluate_js("""
            document.body.style.backgroundColor = '#212121';
            // comment
            function test() {
                return 2 + 2;
            }
            test();
        """)
        assert result == 4
        destroy_event.set()

    t = threading.Thread(target=_evaluate_js, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)

    webview.create_window('Evaluate JS test', 'https://www.example.org')


def test_evaluate_js():
    run_test(evaluate_js)
