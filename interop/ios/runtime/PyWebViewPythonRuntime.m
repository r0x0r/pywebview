#import "PyWebViewPythonRuntime.h"


#if __has_include(<Python/Python.h>)
#import <Python/Python.h>
#define PYWEBVIEW_HAS_PYTHON 1
#else
#define PYWEBVIEW_HAS_PYTHON 0
#endif

#if PYWEBVIEW_HAS_PYTHON
extern PyObject *PyInit_pywebview_ios(void);
#endif

static NSError *PyWebViewRuntimeError(NSString *message) {
    return [NSError errorWithDomain:@"org.pywebview.ios.runtime"
                                code:1
                            userInfo:@{NSLocalizedDescriptionKey: message}];
}

@implementation PyWebViewPythonRuntime

- (BOOL)startWithEntryPoint:(NSString *)entryPoint error:(NSError **)error {
#if !PYWEBVIEW_HAS_PYTHON
    if (error != NULL) {
        *error = PyWebViewRuntimeError(@"Python.xcframework is not linked into this host.");
    }
    return NO;
#else
    NSString *resourcePath = [[NSBundle mainBundle] resourcePath];
    NSString *pythonHome = [resourcePath stringByAppendingPathComponent:@"python"];
    NSString *pythonLib = [pythonHome stringByAppendingPathComponent:@"lib/python3.13"];
    NSString *pythonApp = [resourcePath stringByAppendingPathComponent:@"python/app"];
    NSString *pythonPath = [NSString stringWithFormat:@"%@:%@:%@", pythonLib,
                              [pythonLib stringByAppendingPathComponent:@"lib-dynload"], pythonApp];

    setenv("PYTHONHOME", pythonHome.UTF8String, 1);
    setenv("PYTHONPATH", pythonPath.UTF8String, 1);

    if (PyImport_AppendInittab("pywebview_ios", &PyInit_pywebview_ios) == -1) {
        if (error != NULL) *error = PyWebViewRuntimeError(@"Could not register pywebview_ios.");
        return NO;
    }

    PyPreConfig preConfig;
    PyPreConfig_InitPythonConfig(&preConfig);
    preConfig.utf8_mode = 1;
    PyStatus status = Py_PreInitialize(&preConfig);
    if (PyStatus_Exception(status)) {
        if (error != NULL) *error = PyWebViewRuntimeError(@"Python pre-initialization failed.");
        return NO;
    }

    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.buffered_stdio = 0;
    config.write_bytecode = 0;
    config.install_signal_handlers = 1;
    status = PyConfig_SetBytesString(&config, &config.home, pythonHome.UTF8String);
    if (PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        if (error != NULL) *error = PyWebViewRuntimeError(@"Python configuration failed.");
        return NO;
    }

    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        if (error != NULL) *error = PyWebViewRuntimeError(@"Python initialization failed.");
        return NO;
    }

    PyObject *runpy = PyImport_ImportModule("runpy");
    PyObject *runPath = runpy == NULL ? NULL : PyObject_GetAttrString(runpy, "run_path");
    NSString *entryPath = [entryPoint hasPrefix:@"/"]
        ? entryPoint
        : [resourcePath stringByAppendingPathComponent:entryPoint];
    PyObject *path = PyUnicode_FromString(entryPath.UTF8String);
    PyObject *result = runPath == NULL ? NULL : PyObject_CallFunctionObjArgs(runPath, path, NULL);
    BOOL failed = result == NULL || PyErr_Occurred();
    Py_XDECREF(result);
    Py_XDECREF(path);
    Py_XDECREF(runPath);
    Py_XDECREF(runpy);

    if (failed) {
        if (error != NULL) *error = PyWebViewRuntimeError(@"Python entry point failed.");
        return NO;
    }
    return YES;
#endif
}

- (BOOL)dispatchFunction:(NSString *)functionName
             paramsJSON:(NSString *)paramsJSON
                      id:(NSString *)valueID
                   error:(NSError **)error {
#if !PYWEBVIEW_HAS_PYTHON
    if (error != NULL) {
        *error = PyWebViewRuntimeError(@"Python.xcframework is not linked into this host.");
    }
    return NO;
#else
    PyGILState_STATE gilState = PyGILState_Ensure();
    BOOL success = NO;
    PyObject *webview = PyImport_ImportModule("webview");
    PyObject *windows = webview == NULL ? NULL : PyObject_GetAttrString(webview, "windows");
    PyObject *window = windows == NULL ? NULL : PySequence_GetItem(windows, 0);
    PyObject *util = PyImport_ImportModule("webview.util");
    PyObject *bridge = util == NULL ? NULL : PyObject_GetAttrString(util, "js_bridge_call");
    PyObject *jsonModule = PyImport_ImportModule("json");
    PyObject *loads = jsonModule == NULL ? NULL : PyObject_GetAttrString(jsonModule, "loads");
    PyObject *params = loads == NULL ? NULL : PyObject_CallFunction(loads, "s", paramsJSON.UTF8String);
    PyObject *result = (bridge && window && params)
        ? PyObject_CallFunction(bridge, "OsOs", window, functionName.UTF8String, params, valueID.UTF8String)
        : NULL;

    if (result != NULL) {
        success = YES;
    } else if (error != NULL) {
        *error = PyWebViewRuntimeError(@"Python JavaScript bridge dispatch failed.");
    }

    Py_XDECREF(result);
    Py_XDECREF(params);
    Py_XDECREF(loads);
    Py_XDECREF(jsonModule);
    Py_XDECREF(bridge);
    Py_XDECREF(util);
    Py_XDECREF(window);
    Py_XDECREF(windows);
    Py_XDECREF(webview);
    PyGILState_Release(gilState);
    return success;
#endif
}

- (void)stop {
#if PYWEBVIEW_HAS_PYTHON
    if (Py_IsInitialized()) {
        Py_FinalizeEx();
    }
#endif
}

@end
