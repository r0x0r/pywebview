#!/bin/bash
PYTHONPATH=..
PYWEBVIEW_LOG='debug'
PYTEST_OPTIONS='-s --disable-pytest-warnings -r w'

cd "${0%/*}"
rm -r __pycache__ || true

exitcode=0
pywebviewtest() {
  pytest "$@" || exitcode=$?
}

pywebviewtest test_bg_color.py::test_bg_color ${PYTEST_OPTIONS}
pywebviewtest test_bg_color.py::test_invalid_bg_color ${PYTEST_OPTIONS}

pywebviewtest test_evaluate_js.py::test_mixed ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_array ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_object ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_string ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_int ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_float ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_undefined ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_null ${PYTEST_OPTIONS}
pywebviewtest test_evaluate_js.py::test_nan ${PYTEST_OPTIONS}

pywebviewtest test_frameless.py ${PYTEST_OPTIONS}
pywebviewtest test_fullscreen.py ${PYTEST_OPTIONS}

pywebviewtest test_get_current_url.py::test_current_url ${PYTEST_OPTIONS}
pywebviewtest test_get_current_url.py::test_no_url ${PYTEST_OPTIONS}

pywebviewtest test_get_elements.py::test_single ${PYTEST_OPTIONS}
pywebviewtest test_get_elements.py::test_multiple ${PYTEST_OPTIONS}
pywebviewtest test_get_elements.py::test_none ${PYTEST_OPTIONS}

pywebviewtest test_http_server.py ${PYTEST_OPTIONS}

pywebviewtest test_js_api.py ${PYTEST_OPTIONS}
pywebviewtest test_load_html.py ${PYTEST_OPTIONS}
pywebviewtest test_localization.py ${PYTEST_OPTIONS}
pywebviewtest test_min_size.py ${PYTEST_OPTIONS}

pywebviewtest test_multi_window.py::test_bg_color ${PYTEST_OPTIONS}
pywebviewtest test_multi_window.py::test_load_html ${PYTEST_OPTIONS}
pywebviewtest test_multi_window.py::test_load_url ${PYTEST_OPTIONS}
pywebviewtest test_multi_window.py::test_evaluate_js ${PYTEST_OPTIONS}
pywebviewtest test_multi_window.py::test_js_bridge ${PYTEST_OPTIONS}

pywebviewtest test_noresize.py ${PYTEST_OPTIONS}
pywebviewtest test_on_top.py ${PYTEST_OPTIONS}
pywebviewtest test_set_title.py ${PYTEST_OPTIONS}
pywebviewtest test_resize.py ${PYTEST_OPTIONS}
pywebviewtest test_simple_browser.py ${PYTEST_OPTIONS}
pywebviewtest test_start.py ${PYTEST_OPTIONS}
pywebviewtest test_toggle_fullscreen.py ${PYTEST_OPTIONS}

pywebviewtest test_token.py::test_token ${PYTEST_OPTIONS}
pywebviewtest test_token.py::test_persistance ${PYTEST_OPTIONS}

pywebviewtest test_url_load.py ${PYTEST_OPTIONS}

pywebviewtest test_window.py ${PYTEST_OPTIONS}

pywebviewtest test_wsgi.py ${PYTEST_OPTIONS}

if [ $exitcode != 0 ]; then
  echo -e '\033[0;31mTEST FAILURES HAVE OCCURRED!\033[0m'
  exit 1
fi
