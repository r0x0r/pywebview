# Android test suite

Since pytest based cannot run on Android, this is an alternative browser based Mocha test suite that can be run on Android devices. Tests are written in JavaScript and run in a browser environment. These tests must pass on other platforms as well, but the focus is on Android compatibility.

## Running the tests

Run `runner.py` to start the test runner. This will open a browser window and run the tests. To test on Android, build the app with `runner.py` as an entry point and include all the HTML and JavaScript files in the app's assets. Then, run the app on an Android device.
