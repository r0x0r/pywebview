# Android test suite

Since pytest based cannot run on Android, this is an alternative browser based Mocha test suite that can be run on Android devices. Tests are written in JavaScript and run in a browser environment. These tests must pass on other platforms as well, but the focus is on Android compatibility.

## Running the tests

Run `main.py` to start the test runner. This will open a browser window and run the tests. To test on Android, build the app with `main.py` as an entry point and include all the HTML and JavaScript files in the app's assets. Then, run the app on an Android device.

## Using local network HTTP server

If you want to make changes to the tests and run them on an Android device, you can use a local network HTTP server started by `start_http.py`. Point `main.py` url to the local server URL (e.g., `http://192.168.x.x:1234`) and you can make changes to the tests without rebuilding the app.