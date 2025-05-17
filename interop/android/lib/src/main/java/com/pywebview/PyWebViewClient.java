package com.pywebview;

import android.graphics.Bitmap;
import android.net.http.SslError;
import android.os.Build;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Log;

import java.util.HashMap;
import java.util.Map;
import java.util.List;
import org.json.JSONObject;

public class PyWebViewClient extends WebViewClient {
    private EventCallbackWrapper callback;
    private boolean ignoreSslErrors = false;
    private WebViewRequestInterceptor requestInterceptor;

    public PyWebViewClient() {
        super();
    }

    public void setCallback(EventCallbackWrapper callback, boolean ignoreSslErrors) {
        this.callback = callback;
        this.ignoreSslErrors = ignoreSslErrors;
    }

    public void setRequestInterceptor(WebViewRequestInterceptor interceptor) {
        this.requestInterceptor = interceptor;
    }

    @Override
    public void onPageStarted(WebView view, String url, Bitmap favicon) {
        super.onPageStarted(view, url, favicon);
        if (callback != null) {
            callback.callback("onPageStarted", url);
        }
    }

    @Override
    public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        if (callback != null) {
            callback.callback("onPageFinished", url);
        }
    }

    @Override
    public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
        if (ignoreSslErrors) {
            handler.proceed();
        } else {
            handler.cancel();
        }
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        if (requestInterceptor != null) {
            String url = request.getUrl().toString();
            String method = request.getMethod();

            Map<String, String> headers = new HashMap<>();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                Map<String, String> requestHeaders = request.getRequestHeaders();
                if (requestHeaders != null) {
                    headers.putAll(requestHeaders);
                }
            }

            requestInterceptor.onRequest(url, method, headers);
        }

        return super.shouldInterceptRequest(view, request);
    }

    @Override
    public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
        super.onReceivedHttpError(view, request, errorResponse);

        if (requestInterceptor != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            String url = request.getUrl().toString();
            int statusCode = errorResponse.getStatusCode();

            Map<String, String> headers = new HashMap<>();
            if (errorResponse.getResponseHeaders() != null) {
                headers.putAll(errorResponse.getResponseHeaders());
            }

            requestInterceptor.onResponse(url, statusCode, headers);
        }

        if (callback != null) {
            try {
                JSONObject data = new JSONObject();
                data.put("url", request.getUrl().toString());
                data.put("statusCode", errorResponse.getStatusCode());
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && errorResponse.getResponseHeaders() != null) {
                    JSONObject headers = new JSONObject();
                    for (Map.Entry<String, String> entry : errorResponse.getResponseHeaders().entrySet()) {
                        headers.put(entry.getKey(), entry.getValue());
                    }
                    data.put("headers", headers);
                }

                callback.callback("onReceivedHttpError", data.toString());
            } catch (Exception e) {
                Log.e("PyWebViewClient", "Error creating JSON", e);
            }
        }
    }
}
