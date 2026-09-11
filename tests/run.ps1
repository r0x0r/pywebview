$RootPath = Split-Path $PSScriptRoot
$env:PYTHONPATH = $RootPath
$env:PYWEBVIEW_LOG = 'info'

if (Test-Path __pycache__) {
  Remove-Item -Recurse -Force __pycache__
}

# pytest's exit code alone cannot be trusted for this backend.
# Application.current.exit() in winui3.py's last-window-close teardown tears the
# whole process down as soon as a test has opened and closed a window - before
# pytest prints its summary or sets an exit code. A failing test therefore left
# nothing but a bare 'F' in the log and an exit status of 0, and this script
# called the job green.
#
# The pytest_runtest_logreport hook in conftest.py writes each outcome to this
# file as the test finishes, which survives that teardown. The exit codes are
# still checked as well, for the runs that do get to report normally.
$OutcomeLog = Join-Path ([System.IO.Path]::GetTempPath()) 'pywebview-test-outcomes.tsv'
if (Test-Path $OutcomeLog) { Remove-Item -Force $OutcomeLog }
$env:PYWEBVIEW_TEST_OUTCOME_LOG = $OutcomeLog

# Node ids are relative to rootdir, so keep only the part from the file name on;
# that is stable whether pytest is invoked from here or from the repo root.
function Get-TestKey($NodeId) {
  return ($NodeId -split '/')[-1]
}

$Collected = @(
  python -m pytest --collect-only -q 2>$null |
    Where-Object { $_ -match '::' } |
    ForEach-Object { Get-TestKey $_ }
)

$tests = Get-ChildItem -Path $PSScriptRoot -Filter 'test_*.py' | ForEach-Object { $_.Name }

$ExitCodeErrors = 0
foreach ($test in $tests) {
  Write-Host "Running test: $test"
  python -m pytest $test -q -s --disable-warnings -r w
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  pytest exited with $LASTEXITCODE for $test"
    $ExitCodeErrors = $ExitCodeErrors + 1
  }
}

$Reported = @{}
$Failed = @()
if (Test-Path $OutcomeLog) {
  foreach ($line in Get-Content $OutcomeLog) {
    $parts = $line -split "`t"
    if ($parts.Count -lt 3) { continue }
    $outcome = $parts[0]
    $key = Get-TestKey $parts[2]
    $Reported[$key] = $outcome
    if ($outcome -eq 'failed') { $Failed += "$key ($($parts[1]))" }
  }
}

$NeverRan = @($Collected | Where-Object { -not $Reported.ContainsKey($_) })

Write-Host ''
Write-Host '==== WinUI3 test summary ===='
Write-Host "collected: $($Collected.Count)  reported: $($Reported.Count)  failed: $($Failed.Count)  never ran: $($NeverRan.Count)"

if ($Failed.Count -gt 0) {
  Write-Host ''
  Write-Host 'FAILED:'
  $Failed | ForEach-Object { Write-Host "  $_" }
}

if ($NeverRan.Count -gt 0) {
  # Not a failure: this is the known WinUI3 limitation that only the first test
  # of each file gets to run, because the process exits with the first window.
  # Listing them keeps the size of the gap visible instead of implicit.
  Write-Host ''
  Write-Host 'NEVER RAN (process exited before these could run):'
  $NeverRan | ForEach-Object { Write-Host "  $_" }
}

if ($Failed.Count -gt 0 -or $ExitCodeErrors -gt 0) {
  exit 1
}

exit 0
