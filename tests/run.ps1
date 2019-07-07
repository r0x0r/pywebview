$RootPath = Split-Path $PSScriptRoot
${env:PYTHONPATH='$RootPath'}
${env:PYWEBVIEW_LOG='debug'}

rm -r __pycache__

pytest test_bg_color.py::test_bg_color -s
pytest test_bg_color.py::test_invalid_bg_color -s

pytest test_evaluate_js.py::test_mixed -s
pytest test_evaluate_js.py::test_array -s
pytest test_evaluate_js.py::test_object -s
pytest test_evaluate_js.py::test_string -s
pytest test_evaluate_js.py::test_int -s
pytest test_evaluate_js.py::test_float -s
pytest test_evaluate_js.py::test_undefined -s
pytest test_evaluate_js.py::test_null -s
pytest test_evaluate_js.py::test_nan -s

pytest test_frameless.py -s
pytest test_fullscreen.py -s

pytest test_get_current_url.py::test_current_url -s
pytest test_get_current_url.py::test_no_url -s

pytest test_get_elements.py -s
pytest test_http_server.py -s
pytest test_js_api.py -s
pytest test_load_html.py -s
pytest test_localization.py -s
pytest test_min_size.py -s

pytest test_multi_window.py::test_bg_color -s
pytest test_multi_window.py::test_load_html -s
pytest test_multi_window.py::test_load_url -s
pytest test_multi_window.py::test_evaluate_js -s
pytest test_multi_window.py::test_js_bridge -s

pytest test_noresize.py -s
pytest test_set_title.py -s
pytest test_set_window_size.py -s
pytest test_simple_browser.py -s
pytest test_start.py -s
pytest test_toggle_fullscreen.py -s

pytest test_token.py::test_token -s
pytest test_token.py::test_persistance -s

pytest test_url_load.py -s

pytest test_window.py -s