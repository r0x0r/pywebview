#import <Foundation/Foundation.h>

#if __has_include(<Python/Python.h>)
#include <Python/Python.h>
#define PYWEBVIEW_HAS_PYTHON 1
#else
#define PYWEBVIEW_HAS_PYTHON 0
#endif

#if PYWEBVIEW_HAS_PYTHON

static PyObject *post_request(NSString *name, NSDictionary *userInfo) {
    dispatch_async(dispatch_get_main_queue(), ^{
        [[NSNotificationCenter defaultCenter] postNotificationName:name object:nil userInfo:userInfo];
    });
    Py_RETURN_NONE;
}

static PyObject *setup_app(PyObject *self, PyObject *args) {
    Py_RETURN_NONE;
}

static PyObject *create_window(PyObject *self, PyObject *args) {
    const char *uid;
    const char *title;
    if (!PyArg_ParseTuple(args, "ss", &uid, &title)) return NULL;
    return post_request(@"PyWebViewIOSCreateWindow", @{
        @"uid": [NSString stringWithUTF8String:uid],
        @"title": [NSString stringWithUTF8String:title],
    });
}

static PyObject *load_url(PyObject *self, PyObject *args) {
    const char *url;
    const char *uid;
    if (!PyArg_ParseTuple(args, "ss", &url, &uid)) return NULL;
    return post_request(@"PyWebViewIOSLoadURL", @{
        @"url": [NSString stringWithUTF8String:url],
        @"uid": [NSString stringWithUTF8String:uid],
    });
}

static PyObject *load_html(PyObject *self, PyObject *args) {
    const char *html;
    const char *baseURI;
    const char *uid;
    if (!PyArg_ParseTuple(args, "sss", &html, &baseURI, &uid)) return NULL;
    return post_request(@"PyWebViewIOSLoadHTML", @{
        @"html": [NSString stringWithUTF8String:html],
        @"baseURI": [NSString stringWithUTF8String:baseURI],
        @"uid": [NSString stringWithUTF8String:uid],
    });
}

static PyObject *evaluate_js(PyObject *self, PyObject *args) {
    const char *script;
    PyObject *uid;
    int parseJSON;
    if (!PyArg_ParseTuple(args, "sOp", &script, &uid, &parseJSON)) return NULL;
    __block id result = nil;
    __block NSError *evaluationError = nil;
    dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
    void (^reply)(id, NSError *) = ^(id value, NSError *error) {
        result = value;
        evaluationError = error;
        dispatch_semaphore_signal(semaphore);
    };

    NSDictionary *request = @{
        @"script": [NSString stringWithUTF8String:script],
        @"parseJSON": @(parseJSON),
        @"reply": [reply copy],
    };
    dispatch_async(dispatch_get_main_queue(), ^{
        [[NSNotificationCenter defaultCenter] postNotificationName:@"PyWebViewIOSEvaluateJS" object:nil userInfo:request];
    });

    if (dispatch_semaphore_wait(semaphore, dispatch_time(DISPATCH_TIME_NOW, 20 * NSEC_PER_SEC)) != 0) {
        PyErr_SetString(PyExc_TimeoutError, "Timed out waiting for iOS JavaScript evaluation");
        return NULL;
    }
    if (evaluationError != nil) {
        PyErr_SetString(PyExc_RuntimeError, evaluationError.localizedDescription.UTF8String);
        return NULL;
    }

    if (result == nil || result == [NSNull null]) Py_RETURN_NONE;
    NSData *jsonData = [NSJSONSerialization dataWithJSONObject:result options:0 error:&evaluationError];
    if (jsonData == nil) {
        PyErr_SetString(PyExc_RuntimeError, "iOS JavaScript result is not JSON serializable");
        return NULL;
    }
    NSString *json = [[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
    if (!parseJSON) return PyUnicode_FromString(json.UTF8String);

    PyObject *jsonModule = PyImport_ImportModule("json");
    PyObject *loads = jsonModule == NULL ? NULL : PyObject_GetAttrString(jsonModule, "loads");
    PyObject *value = loads == NULL ? NULL : PyObject_CallFunction(loads, "s", json.UTF8String);
    Py_XDECREF(loads);
    Py_XDECREF(jsonModule);
    return value;
}

static PyObject *empty_result(PyObject *self, PyObject *args) {
    Py_RETURN_NONE;
}

static PyObject *empty_list(PyObject *self, PyObject *args) {
    return PyList_New(0);
}

static PyObject *size_result(PyObject *self, PyObject *args) {
    return Py_BuildValue("(ii)", 0, 0);
}

static PyMethodDef methods[] = {
    {"setup_app", setup_app, METH_NOARGS, "Register the native iOS host."},
    {"create_window", create_window, METH_VARARGS, "Create the native WebView."},
    {"load_url", load_url, METH_VARARGS, "Load a URL in the native WebView."},
    {"load_html", load_html, METH_VARARGS, "Load HTML in the native WebView."},
    {"evaluate_js", evaluate_js, METH_VARARGS, "Evaluate JavaScript in the native WebView."},
    {"destroy_window", empty_result, METH_VARARGS, "Destroy the native WebView."},
    {"clear_cookies", empty_result, METH_VARARGS, "Clear WebKit cookies."},
    {"get_cookies", empty_list, METH_VARARGS, "Return WebKit cookies."},
    {"get_current_url", empty_result, METH_VARARGS, "Return the current URL."},
    {"get_screens", empty_list, METH_VARARGS, "Return screen information."},
    {"get_size", size_result, METH_VARARGS, "Return WebView dimensions."},
    {"set_title", empty_result, METH_VARARGS, "Set native title metadata."},
    {"show", empty_result, METH_VARARGS, "Show the native host."},
    {"hide", empty_result, METH_VARARGS, "Hide the native host."},
    {"toggle_fullscreen", empty_result, METH_VARARGS, "Toggle fullscreen."},
    {"create_confirmation_dialog", empty_result, METH_VARARGS, "Show a confirmation dialog."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "pywebview_ios",
    "Native iOS operations for pywebview.",
    -1,
    methods,
};

PyMODINIT_FUNC PyInit_pywebview_ios(void) {
    return PyModule_Create(&module);
}
#else
// The host-only simulator build deliberately omits Python.xcframework.
// This translation unit becomes the real extension when the framework is
// staged and the Python headers are available.
int pywebview_ios_runtime_placeholder(void) {
    return 0;
}
#endif
