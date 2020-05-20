#!/bin/bash
PYTHONPATH=..
PYWEBVIEW_LOG='debug'
PYTEST_OPTIONS='-s --disable-pytest-warnings -r w'

cd "${0%/*}"
rm -r __pycache__ || true

pytest test_bg_color.py::test_bg_color ${PYTEST_OPTIONS}
pytest test_bg_color.py::test_invalid_bg_color ${PYTEST_OPTIONS}

pytest test_evaluate_js.py::test_mixed ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_array ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_object ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_string ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_int ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_float ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_undefined ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_null ${PYTEST_OPTIONS}
pytest test_evaluate_js.py::test_nan ${PYTEST_OPTIONS}

pytest test_frameless.py ${PYTEST_OPTIONS}
pytest test_fullscreen.py ${PYTEST_OPTIONS}

pytest test_get_current_url.py::test_current_url ${PYTEST_OPTIONS}
pytest test_get_current_url.py::test_no_url ${PYTEST_OPTIONS}

pytest test_get_elements.py::test_single ${PYTEST_OPTIONS}
pytest test_get_elements.py::test_multiple ${PYTEST_OPTIONS}
pytest test_get_elements.py::test_none ${PYTEST_OPTIONS}

pytest test_http_server.py ${PYTEST_OPTIONS}

pytest test_js_api.py ${PYTEST_OPTIONS}
pytest test_load_html.py ${PYTEST_OPTIONS}
pytest test_localization.py ${PYTEST_OPTIONS}
pytest test_min_size.py ${PYTEST_OPTIONS}

pytest test_multi_window.py::test_bg_color ${PYTEST_OPTIONS}
pytest test_multi_window.py::test_load_html ${PYTEST_OPTIONS}
pytest test_multi_window.py::test_load_url ${PYTEST_OPTIONS}
pytest test_multi_window.py::test_evaluate_js ${PYTEST_OPTIONS}
pytest test_multi_window.py::test_js_bridge ${PYTEST_OPTIONS}

pytest test_noresize.py ${PYTEST_OPTIONS}
pytest test_on_top.py ${PYTEST_OPTIONS}
pytest test_set_title.py ${PYTEST_OPTIONS}
pytest test_set_window_size.py ${PYTEST_OPTIONS}
pytest test_simple_browser.py ${PYTEST_OPTIONS}
pytest test_start.py ${PYTEST_OPTIONS}
pytest test_toggle_fullscreen.py ${PYTEST_OPTIONS}

pytest test_token.py::test_token ${PYTEST_OPTIONS}
pytest test_token.py::test_persistance ${PYTEST_OPTIONS}

pytest test_url_load.py ${PYTEST_OPTIONS}

pytest test_window.py ${PYTEST_OPTIONS}
