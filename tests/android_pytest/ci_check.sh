#!/usr/bin/env bash
# Installs and runs the built pytest APK on a booted emulator/device, tails
# logcat for the PYWEBVIEW_TEST_RESULT:: markers main.py prints (see its
# docstring for why logcat instead of a pulled file), and exits non-zero on
# any failed test or on timing out without a DONE marker.
#
# Expects an APK at bin/*.apk (buildozer's default output path) and a
# reachable adb device. Run from tests/android_pytest/.
set -euo pipefail

PACKAGE="com.pywebview.pywebviewpytest"
ACTIVITY="org.kivy.android.PythonActivity"
TIMEOUT_SECONDS="${PYWEBVIEW_ANDROID_TEST_TIMEOUT:-600}"
LOGCAT_FILE="$(mktemp)"

shopt -s nullglob
APKS=(bin/*.apk)
shopt -u nullglob
if [ ${#APKS[@]} -eq 0 ]; then
  echo "No APK found under bin/ - did the buildozer build step run?" >&2
  exit 1
fi
APK="${APKS[0]}"

echo "Installing $APK"
adb install -r "$APK"

adb logcat -c
timeout "$TIMEOUT_SECONDS" adb logcat -v raw > "$LOGCAT_FILE" &
LOGCAT_PID=$!

echo "Launching $PACKAGE/$ACTIVITY"
adb shell am start -n "$PACKAGE/$ACTIVITY"

echo "Waiting for PYWEBVIEW_TEST_RESULT::DONE (timeout ${TIMEOUT_SECONDS}s)"
elapsed=0
while ! grep -q 'PYWEBVIEW_TEST_RESULT::DONE' "$LOGCAT_FILE" 2>/dev/null; do
  if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
    echo "Timed out waiting for the test run to finish." >&2
    echo "--- last 200 log lines ---" >&2
    tail -n 200 "$LOGCAT_FILE" >&2
    kill "$LOGCAT_PID" 2>/dev/null || true
    exit 1
  fi
  sleep 5
  elapsed=$((elapsed + 5))
done

kill "$LOGCAT_PID" 2>/dev/null || true
wait "$LOGCAT_PID" 2>/dev/null || true

echo "--- test results ---"
grep 'PYWEBVIEW_TEST_RESULT::' "$LOGCAT_FILE" || true

# DONE::<exitstatus>::<passed>::<failed>, so awk -F'::' sees $2=DONE, $3=exit,
# $4=passed, $5=failed.
DONE_LINE="$(grep 'PYWEBVIEW_TEST_RESULT::DONE' "$LOGCAT_FILE" | tail -n1)"
EXIT_STATUS="$(echo "$DONE_LINE" | awk -F'::' '{print $3}')"
PASSED_COUNT="$(echo "$DONE_LINE" | awk -F'::' '{print $4}')"
FAILED_COUNT="$(echo "$DONE_LINE" | awk -F'::' '{print $5}')"

if [ -z "$FAILED_COUNT" ] || [ "$FAILED_COUNT" != "0" ]; then
  echo "${FAILED_COUNT:-?} test(s) failed." >&2
  exit 1
fi

# The failed count alone is not enough: a collection/import error ends the
# session with exitstatus 2 and zero reported tests, which would otherwise read
# as a clean run. Require pytest to have exited 0 *and* to have actually run
# something.
if [ "$EXIT_STATUS" != "0" ]; then
  echo "pytest exited with status ${EXIT_STATUS:-?} (collection or internal error)." >&2
  exit 1
fi

if [ -z "$PASSED_COUNT" ] || [ "$PASSED_COUNT" -eq 0 ]; then
  echo "No tests ran - refusing to report success." >&2
  exit 1
fi

echo "All $PASSED_COUNT tests passed."
