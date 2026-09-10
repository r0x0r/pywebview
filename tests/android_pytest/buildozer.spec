[app]
title = pywebview android pytest suite
package.name = pywebviewpytest
package.domain = com.pywebview
source.dir = ./
source.include_exts = py,png,jpg,html,jar
source.exclude_dirs = bin,build,dist,.venv,venv,__pycache__
version = 0.1

# pytest and its own runtime deps (kept explicit rather than relying on p4a's
# transitive resolution for the generic/pip recipe path, which is less
# reliable than it is for plain pip).
requirements = python3,bottle,proxy_tools,typing_extensions,cryptography,pytest,iniconfig,pluggy,packaging

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
