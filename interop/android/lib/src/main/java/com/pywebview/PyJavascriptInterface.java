package com.pywebview;

import com.pywebview.JsApiCallbackWrapper;
import android.webkit.JavascriptInterface;
import android.util.Log;


public class PyJavascriptInterface {
  private JsApiCallbackWrapper callbackWrapper = null;

  public void setCallback(JsApiCallbackWrapper callback) {
      this.callbackWrapper = callback;
  }

  @JavascriptInterface
  public void call(String func, String params, String id) {
      if (this.callbackWrapper != null) {
          this.callbackWrapper.callback(func, params, id);
      } else {
        Log.e("python", "No callback");
      }
  }

}
