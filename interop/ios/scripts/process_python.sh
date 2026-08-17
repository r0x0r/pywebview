#!/bin/sh

set -eu

project_dir="${PROJECT_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
framework="$project_dir/Python.xcframework"
app_dir="$project_dir/python/app"

if [ ! -d "$framework" ]; then
    echo "Python.xcframework not staged; skipping embedded Python processing."
    exit 0
fi

if [ ! -d "$app_dir" ]; then
    echo "Python application directory is missing: $app_dir" >&2
    exit 1
fi

build_utils="$framework/build/build_utils.sh"
if [ ! -f "$build_utils" ]; then
    echo "Python framework build utilities are missing: $build_utils" >&2
    exit 1
fi

# install_python selects the correct device/simulator framework slice and
# processes the standard library and application modules into the app bundle.
# shellcheck disable=SC1090
. "$build_utils"
install_python "$framework" "$app_dir"
