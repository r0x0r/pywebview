package com.pywebview;

import android.app.AlertDialog;
import android.app.Activity;
import android.content.DialogInterface;
import android.util.Log;
import android.view.View.OnClickListener;
import android.webkit.JsResult;
import android.webkit.WebView;
import android.webkit.WebChromeClient;


public class PyWebChromeClient extends WebChromeClient {
    private EventCallbackWrapper callbackWrapper = null;

    public void setCallback(EventCallbackWrapper callback) {
        this.callbackWrapper = callback;
    }

    @Override
    public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
        // TODO: This code crashes the app.

        Activity context = (Activity)view.getContext();
        new AlertDialog.Builder(context)
              .setMessage(message)
              .setPositiveButton(android.R.string.ok, (dialog, which) -> result.confirm())
              .setOnCancelListener(dialog -> result.cancel())
              .show();

        return true;
    }

    @Override
    public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
        new AlertDialog.Builder(view.getContext())
                .setMessage(message)
                .setPositiveButton(android.R.string.ok, (dialog, which) -> result.confirm())
                .setNegativeButton(android.R.string.cancel, (dialog, which) -> result.cancel())
                .setOnCancelListener(dialog -> result.cancel())
                .show();
        return true;
    }

    // @Override
    // public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
    //     LayoutInflater inflater = LayoutInflater.from(context);
    //     View promptView = inflater.inflate(R.layout.dialog_js_prompt, null, false);
    //     TextView messageView = promptView.findViewById(R.id.message);
    //     messageView.setText(message);
    //     final EditText valueView = promptView.findViewById(R.id.value);
    //     valueView.setText(defaultValue);

    //     new AlertDialog.Builder(context)
    //             .setView(promptView)
    //             .setPositiveButton(android.R.string.ok, (dialog, which) -> result.confirm(valueView.getText().toString()))
    //             .setOnCancelListener(dialog -> result.cancel())
    //             .show();

    //     return true;
    // }

}


