[app]
title = pywebview android pytest suite
package.name = pywebviewpytest
package.domain = com.pywebview
source.dir = ./
# js is required: load_js_files() globs webview/js/**/*.js relative to the
# installed webview package, and without those files nothing gets injected into
# the page, so window.pywebview never exists and every test hangs on
# events.loaded. tests/android/buildozer.spec includes it for the same reason.
source.include_exts = py,png,jpg,html,jar,js
source.exclude_dirs = bin,build,dist,.venv,venv,__pycache__
version = 0.1

# pytest is pinned and its runtime dependencies listed explicitly rather than
# left to p4a's transitive resolution, which is less reliable than plain pip
# for arbitrary sdists. pygments is easy to miss - pytest has required it since
# 8.4. exceptiongroup and tomli are only needed below Python 3.11; they are
# harmless above it and cheap insurance against whichever version p4a's python3
# recipe currently builds. colorama is win32-only and deliberately omitted.
#
# Note the absence of cryptography, which tests/android/buildozer.spec needs:
# pywebview only imports it inside __generate_ssl_cert(), and this suite never
# passes ssl=True. There is no p4a recipe for it, so it would be built from an
# sdist and need a Rust toolchain cross-compiled for Android.
requirements = python3,bottle,proxy_tools,typing_extensions,pytest==9.1.1,iniconfig,pluggy,packaging,pygments,exceptiongroup,tomli

orientation = portrait,landscape
osx.python_version = 3
fullscreen = 0
android.presplash_color =
android.permissions = android.permission.INTERNET
android.apptheme = @android:style/Theme.Material.NoActionBar
android.add_jars = ../../webview/lib/pywebview-android.jar
# arm64-v8a/armeabi-v7a for real devices; x86_64 so this also runs at native
# speed on the KVM-accelerated x86_64 AVD used in GitHub Actions CI - an
# ARM-only APK would run there too, but only via slow QEMU translation.
android.archs = arm64-v8a, armeabi-v7a, x86_64
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
