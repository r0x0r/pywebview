[app]
title = pywebview android app
package.name = app
package.domain = com.pywebview
source.dir = ./
source.include_exts = py,png,jpg,html,jar,js
source.include_patterns = tests/*
source.exclude_exts = spec,
source.exclude_dirs = bin,build,dist,.venv,venv
#source.exclude_patterns =
version = 0.1

requirements = python3,bottle,proxy_tools,typing_extensions,cryptography,pyjnius,android

orientation = portrait,landscape
osx.python_version = 3
fullscreen = 0
android.presplash_color =
android.permissions = android.permission.INTERNET, (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=18)
android.apptheme = @android:style/Theme.Material.NoActionBar
android.add_jars = ../../webview/lib/pywebview-android.jar
#android.extra_manifest_xml = ./manifest.xml
# Android blocks cleartext HTTP to the local server for targetSdk >= 28. Passed via p4a.extra_args
# because buildozer's android.extra_manifest_application_arguments wraps the value in literal
# quotes, which breaks the generated AndroidManifest.xml.
p4a.extra_args = --extra-manifest-application-arguments='android:usesCleartextTraffic="true"'
android.archs = arm64-v8a
android.allow_backup = True
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
ios.codesign.allowed = false
[buildozer]
log_level = 2
warn_on_root = 1
