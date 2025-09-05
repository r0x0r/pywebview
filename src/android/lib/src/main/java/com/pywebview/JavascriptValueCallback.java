package com.pywebview;

import com.pywebview.EventCallbackWrapper;
import android.webkit.ValueCallback;
import android.util.Log;

public class JavascriptValueCallback implements ValueCallback<String> {
    private EventCallbackWrapper callbackWrapper = null;

    public void setCallback(EventCallbackWrapper callback) {
        this.callbackWrapper = callback;
    }

    @Override
    public void onReceiveValue(String value) {
        if (this.callbackWrapper != null) {
            this.callbackWrapper.callback("onReceiveValue", value);
        }
    }
}