#!/usr/bin/env bash
# Installs and runs the built pytest APK on a booted emulator/device, tails
# logcat for the PYWEBVIEW_TEST_RESULT:: markers main.py prints, and exits
# non-zero on any failed test or on timing out without a DONE marker.
#
# Expects an APK at bin/*.apk and a reachable adb device. Run from tests/android/.
set -euo pipefail

PACKAGE="com.pywebview.pywebviewpytest"
ACTIVITY="org.kivy.android.PythonActivity"
TIMEOUT_SECONDS="${PYWEBVIEW_ANDROID_TEST_TIMEOUT:-600}"
# Under the working directory rather than mktemp, so CI can upload it whole.
LOGCAT_FILE="${PYWEBVIEW_ANDROID_LOGCAT:-logcat.txt}"
SUMMARY_FILE="${PYWEBVIEW_ANDROID_SUMMARY:-summary.md}"
LOGCAT_PID=""
LIVE_PID=""

dump_log_tail() {
  echo "--- last 200 log lines ---" >&2
  tail -n 200 "$LOGCAT_FILE" >&2 || true
}

stop_logcat() {
  for pid in "$LIVE_PID" "$LOGCAT_PID"; do
    if [ -n "$pid" ]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  LIVE_PID=""
  LOGCAT_PID=""
}

# A reader still attached to the device keeps the CI step's shell open.
trap stop_logcat EXIT

# Everything the app writes, echoed as it happens, so a hang is diagnosable
# before the artifact exists. python is the tag p4a gives the interpreter's
# stdout, so it carries pytest's output; AndroidRuntime carries Java crashes.
start_live_log() {
  # Process substitution rather than a pipeline so that $! is adb's own pid.
  adb logcat -v threadtime -s python:D AndroidRuntime:V 2>/dev/null \
    > >(awk '{ print "[device] " $0; fflush() }') &
  LIVE_PID=$!
}

# The marker payload with the logcat prefix stripped, so parsing does not
# depend on the -v format.
marker_lines() {
  sed -n "s/.*PYWEBVIEW_TEST_RESULT::$1:://p" "$LOGCAT_FILE" 2>/dev/null || true
}

# Written to a file rather than straight to $GITHUB_STEP_SUMMARY, which the
# emulator action is not guaranteed to pass down to us. The workflow appends it.
write_step_summary() {
  local status="$1"

  local failures app_log session
  failures="$(marker_lines FAIL | sed 's/^/- /')"

  app_log="$(grep -E ' [VDIWEF] python +: ' "$LOGCAT_FILE" 2>/dev/null || true)"
  # From the START marker. Everything before it is p4a unpacking its assets.
  session="$(printf '%s\n' "$app_log" | sed -n '/PYWEBVIEW_TEST_RESULT::START/,$p')"
  [ -n "$session" ] || session="$app_log"

  {
    echo "### Android tests: ${status}"
    echo
    if [ -n "$failures" ]; then
      echo "Failed:"
      echo
      echo "$failures"
      echo
    fi
    echo "<details><summary>Device log</summary>"
    echo
    echo '```'
    printf '%s\n' "$session" | tail -n 400
    echo '```'
    echo
    echo "</details>"
  } > "$SUMMARY_FILE"
}

done_marker_present() {
  grep -q 'PYWEBVIEW_TEST_RESULT::DONE' "$LOGCAT_FILE" 2>/dev/null
}

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

# install -r keeps the app's data directory - including WebView's cookie store -
# and can leave the previous run's activity alive to write its own result markers
# into the buffer we are about to read. The cookie tests assert exact counts, so
# a reused device has to start from clean state. Run after install so the package
# exists on a fresh emulator too.
adb shell pm clear "$PACKAGE"

adb logcat -c
: > "$LOGCAT_FILE"
# threadtime carries a timestamp, the tag and the thread id, which is what
# distinguishes the UI thread from the test threads when chasing a JNI problem.
timeout "$TIMEOUT_SECONDS" adb logcat -v threadtime > "$LOGCAT_FILE" &
LOGCAT_PID=$!
start_live_log

# Launching before logcat has attached can lose the early markers. A silent
# buffer is possible, so this only bounds the wait.
attach_wait=0
while [ ! -s "$LOGCAT_FILE" ]; do
  if [ "$attach_wait" -ge 30 ]; then
    echo "logcat produced no output within 30s; launching anyway." >&2
    break
  fi
  sleep 1
  attach_wait=$((attach_wait + 1))
done

echo "Launching $PACKAGE/$ACTIVITY"
adb shell am start -n "$PACKAGE/$ACTIVITY"

echo "Waiting for PYWEBVIEW_TEST_RESULT::DONE (timeout ${TIMEOUT_SECONDS}s)"
elapsed=0
while ! done_marker_present; do
  if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
    echo "Timed out waiting for the test run to finish." >&2
    dump_log_tail
    stop_logcat
    write_step_summary "timed out after ${TIMEOUT_SECONDS}s"
    exit 1
  fi

  # A crash would otherwise cost the whole timeout. The grace period covers the
  # process not having appeared yet; the re-check covers DONE and exit landing
  # in the same poll interval.
  if [ "$elapsed" -ge 30 ] && ! adb shell pidof "$PACKAGE" > /dev/null 2>&1; then
    sleep 2
    if done_marker_present; then
      break
    fi
    echo "$PACKAGE is no longer running and never reported DONE - it crashed" >&2
    echo "or was killed. Check the uploaded logcat for a Python traceback." >&2
    dump_log_tail
    stop_logcat
    write_step_summary "the app crashed before reporting a result"
    exit 1
  fi

  sleep 5
  elapsed=$((elapsed + 5))
done

stop_logcat

echo "--- test results ---"
grep 'PYWEBVIEW_TEST_RESULT::' "$LOGCAT_FILE" || true

# DONE::<exitstatus>::<passed>::<failed>
DONE_LINE="$(marker_lines DONE | tail -n1)"
EXIT_STATUS="$(echo "$DONE_LINE" | awk -F'::' '{print $1}')"
PASSED_COUNT="$(echo "$DONE_LINE" | awk -F'::' '{print $2}')"
FAILED_COUNT="$(echo "$DONE_LINE" | awk -F'::' '{print $3}')"

if [ -z "$FAILED_COUNT" ] || [ "$FAILED_COUNT" != "0" ]; then
  echo "${FAILED_COUNT:-?} test(s) failed." >&2
  write_step_summary "${FAILED_COUNT:-?} failed, ${PASSED_COUNT:-0} passed"
  exit 1
fi

# The failed count alone is not enough: a collection error ends the session with
# exitstatus 2 and zero reported tests, which would read as a clean run.
if [ "$EXIT_STATUS" != "0" ]; then
  echo "pytest exited with status ${EXIT_STATUS:-?} (collection or internal error)." >&2
  write_step_summary "pytest exited with status ${EXIT_STATUS:-?}"
  exit 1
fi

if [ -z "$PASSED_COUNT" ] || [ "$PASSED_COUNT" -eq 0 ]; then
  echo "No tests ran - refusing to report success." >&2
  write_step_summary "no tests ran"
  exit 1
fi

write_step_summary "$PASSED_COUNT passed"
echo "All $PASSED_COUNT tests passed."
