$RootPath = Split-Path $PSScriptRoot
${env:PYTHONPATH='$RootPath'}
${env:PYWEBVIEW_LOG='debug'}
$tests = Get-ChildItem -Path $PSScriptRoot -Filter 'test_*.py' | ForEach-Object { $_.Name }

if (Test-Path __pycache__) {
  Remove-Item -Recurse -Force __pycache__
}

$errors = 0
foreach ($test in $tests) {
  pytest $test -q -s --disable-warnings -r w
  $errors = $errors + $LASTEXITCODE
}

exit $errors
