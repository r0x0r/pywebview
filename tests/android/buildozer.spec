[app]
title = pywebview android pytest suite
package.name = pywebviewpytest
package.domain = com.pywebview
source.dir = ./
# js is required: without webview/js/**/*.js nothing is injected into the page,
# so window.pywebview never exists and every test hangs on events.loaded.
source.include_exts = py,png,jpg,html,jar,js
source.exclude_dirs = bin,build,dist,.venv,venv,__pycache__
version = 0.1

# pytest's runtime dependencies are listed explicitly rather than left to p4a's
# transitive resolution, which is less reliable than pip for arbitrary sdists.
# exceptiongroup and tomli are only needed below Python 3.11 and are harmless
# above it; colorama is win32-only and omitted.
#
# No cryptography, and so no ssl=True: its Rust extension cannot be loaded by
# the interpreter p4a ships (cannot locate symbol "_Py_DecRef"). Cleartext is
# granted through the manifest instead, see below.
#
# android and pyjnius are what webview/platforms/android imports. The sdl2
# bootstrap does not pull them in on its own.
requirements = python3,android,pyjnius,bottle,proxy_tools,typing_extensions,pytest==9.1.1,iniconfig,pluggy,packaging,pygments,exceptiongroup,tomli

orientation = portrait,landscape
osx.python_version = 3
fullscreen = 0
android.presplash_color =
android.permissions = android.permission.INTERNET
# Android refuses cleartext HTTP for targetSdk >= 28, which would block the
# tests running against pywebview's local server. Injects into the <application>
# tag; android.extra_manifest_xml injects into <manifest> and would not work.
android.extra_manifest_application_arguments = ./manifest_application.xml
# Required for an unattended build. Without it build-tools is never installed
# and the build fails later with "Aidl not found".
android.accept_sdk_license = True
# p4a otherwise byte-compiles with `-OO` and ships only .pyc: pytest collects by
# filename and so finds nothing, and -OO strips every assert statement.
android.no-byte-compile-python = True
android.apptheme = @android:style/Theme.Material.NoActionBar
android.add_jars = ../../webview/lib/pywebview-android.jar
# x86_64 so this runs at native speed on the KVM-accelerated AVD used in CI.
android.archs = arm64-v8a, armeabi-v7a, x86_64
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
