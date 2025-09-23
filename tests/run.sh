#!/bin/bash
PYTHONPATH=..
PYTEST_OPTIONS='-q -s --disable-warnings -r w'

# cd "${0%/*}"
# rm -r __pycache__ || true

exitcode=0
pywebviewtest() {
  python3 -m pytest ${PYTEST_OPTIONS} "$@" || exitcode=$?
}

# cd ..
echo Starting tests...
for test in $(ls test_*); do
echo $test
  pywebviewtest $test
done

if [ $exitcode != 0 ]; then
  echo -e '\033[0;31mTEST FAILURES HAVE OCCURRED!\033[0m'
  exit 1
fi
