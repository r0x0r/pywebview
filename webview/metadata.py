"""
PyObjC metadata for manual loading

Older versions of PyObjC does not ship with the metadata of some methods required
by pywebview. This script contains the metadata dictionaries for these methods to
be loaded manually in case they are unavailable.

(Definitions copied from a newer version of PyObjC)
"""

# [WKWebView evaluateJavaScript:completionHandler:]
eval_js_metadata = {
    "arguments": {
        3: {
            "callable": {
                "retval": { "type": b"v" },
                "arguments": {
                    0: {"type": b"^v"},
                    1: {"type": b"@"},
                    2: {"type": b"@"}
                }
            },
        }
    }
}
