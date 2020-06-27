$RootPath = Split-Path $PSScriptRoot
${env:PYTHONPATH='$RootPath'}
${env:PYWEBVIEW_LOG='debug'}

$tests=@(
  "test_bg_color.py::test_bg_color",
  "test_bg_color.py::test_invalid_bg_color",
  "test_evaluate_js.py::test_mixed",
  "test_evaluate_js.py::test_array",
  "test_evaluate_js.py::test_object",
  "test_evaluate_js.py::test_string",
  "test_evaluate_js.py::test_int",
  "test_evaluate_js.py::test_float",
  "test_evaluate_js.py::test_undefined",
  "test_evaluate_js.py::test_null",
  "test_evaluate_js.py::test_nan",
  "test_frameless.py",
  "test_fullscreen.py",
  "test_get_current_url.py::test_current_url",
  "test_get_current_url.py::test_no_url",
  "test_get_elements.py",
  "test_js_api.py::test_js_bridge",
  "test_js_api.py::test_exception",
  "test_load_html.py",
  "test_localization.py",
  "test_min_size.py",
  "test_move_window.py::test_xy",
  "test_move_window.py::test_move_window",
  "test_multi_window.py::test_bg_color",
  "test_multi_window.py::test_load_html",
  "test_multi_window.py::test_load_url",
  "test_multi_window.py::test_evaluate_js",
  "test_multi_window.py::test_js_bridge",
  "test_noresize.py",
  "test_on_top.py",
  "test_set_title.py",
  "test_resize.py",
  "test_simple_browser.py",
  "test_start.py",
  "test_toggle_fullscreen.py",
  "test_token.py::test_token",
  "test_token.py::test_persistance",
  "test_url_load.py",
  "test_window.py",
  "test_wsgi.py"
)

This test fails with CEF on AppVeyor. Skip it for now
if ($env:PYWEBVIEW_GUI -ne 'cef') {
 $tests += "test_http_server.py"
}

rm -r __pycache__

$errors = 0
foreach ($test in $tests) {
  pytest $test -s
  $errors = $errors + $LASTEXITCODE
}

exit $errors

