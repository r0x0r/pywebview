[app]
title = pywebview android tests
package.name = tests
package.domain = com.pywebview
source.dir = ./
source.include_exts = py,png,jpg,html,jar,js
source.include_patterns = tests/*
source.exclude_exts = spec,
source.exclude_dirs = bin,build,dist,.venv,venv
#source.exclude_patterns =
version = 0.1

# Set here absolute path to pywebview project dir
requirements = python3,bottle,proxy_tools,typing_extensions,cryptography

orientation = portrait,landscape
osx.python_version = 3
fullscreen = 0
android.presplash_color =
android.permissions = android.permission.INTERNET, (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=18)
android.apptheme = @android:style/Theme.Material.NoActionBar
android.add_jars = ../../webview/lib/pywebview-android.jar
#android.extra_manifest_xml = ./manifest.xml
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
adb
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
ios.codesign.allowed = false
[buildozer]
log_level = 2
warn_on_root = 1
