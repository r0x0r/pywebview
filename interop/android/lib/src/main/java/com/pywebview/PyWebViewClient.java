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

import java.io.InputStream;
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
        if (requestInterceptor == null) {
            return super.shouldInterceptRequest(view, request);
        }

        String url = request.getUrl().toString();
        String method = request.getMethod();

        // Collect original request headers
        Map<String, String> headers = new HashMap<>();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && request.getRequestHeaders() != null) {
            headers.putAll(request.getRequestHeaders());
        }

        try {
            // Get modified headers from interceptor
            String headersJson = new JSONObject(headers).toString();
            String newHeaders = requestInterceptor.onRequest(url, method, headersJson);

            if (newHeaders == null) {
                // No interception needed, use default response
                return handleDefaultResponse(view, request);
            }

            // Process intercepted request
            return performCustomRequest(url, method, newHeaders);

        } catch (Exception e) {
            Log.e("PyWebViewClient", "Error intercepting request", e);
            notifyInterceptorOfError(url, e);
            return super.shouldInterceptRequest(view, request);
        }
    }

    private WebResourceResponse handleDefaultResponse(WebView view, WebResourceRequest request) {
        WebResourceResponse response = super.shouldInterceptRequest(view, request);

        try {
            String url = request.getUrl().toString();
            int statusCode = 200;
            Map<String, String> responseHeaders = new HashMap<>();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && response != null) {
                statusCode = response.getStatusCode();
                if (response.getResponseHeaders() != null) {
                    responseHeaders.putAll(response.getResponseHeaders());
                }
            }

            String responseHeadersJson = new JSONObject(responseHeaders).toString();
            requestInterceptor.onResponse(url, statusCode, responseHeadersJson);
        } catch (Exception e) {
            Log.e("PyWebViewClient", "Error processing default response", e);
        }

        return response;
    }

    private WebResourceResponse performCustomRequest(String url, String method, String headersJson) throws Exception {
        JSONObject headersObj = new JSONObject(headersJson);
        Log.e("PyWebViewClient", "Intercepted headers: " + headersObj.toString());

        // Create and configure connection
        java.net.URL urlObj = new java.net.URL(url);
        java.net.HttpURLConnection connection = (java.net.HttpURLConnection) urlObj.openConnection();
        connection.setRequestMethod(method);

        // Set headers
        java.util.Iterator<String> keys = headersObj.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            connection.setRequestProperty(key, headersObj.getString(key));
        }

        connection.connect();

        // Process response
        String contentType = connection.getContentType();
        String mimeType = contentType;
        String encoding = connection.getContentEncoding();

        // Parse content type
        if (contentType != null && contentType.contains(";")) {
            mimeType = contentType.split(";")[0].trim();
            if (encoding == null && contentType.toLowerCase().contains("charset=")) {
                for (String part : contentType.split(";")) {
                    if (part.toLowerCase().contains("charset=")) {
                        encoding = part.split("=")[1].trim();
                        break;
                    }
                }
            }
        }

        InputStream inputStream = connection.getInputStream();
        int statusCode = connection.getResponseCode();
        String reasonPhrase = connection.getResponseMessage();

        // Collect response headers
        Map<String, String> responseHeaders = new HashMap<>();
        for (Map.Entry<String, List<String>> entry : connection.getHeaderFields().entrySet()) {
            if (entry.getKey() != null && !entry.getValue().isEmpty()) {
                responseHeaders.put(entry.getKey(), entry.getValue().get(0));
            }
        }

        // Notify interceptor
        requestInterceptor.onResponse(url, statusCode, new JSONObject(responseHeaders).toString());

        // Return appropriate response based on API level
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            return new WebResourceResponse(mimeType, encoding, statusCode, reasonPhrase, responseHeaders, inputStream);
        } else {
            return new WebResourceResponse(mimeType, encoding, inputStream);
        }
    }

    private void notifyInterceptorOfError(String url, Exception e) {
        try {
            JSONObject errorInfo = new JSONObject();
            errorInfo.put("error", e.getMessage());
            requestInterceptor.onResponse(url, 0, errorInfo.toString());
        } catch (Exception jsonEx) {
            Log.e("PyWebViewClient", "Error creating JSON for error response", jsonEx);
        }
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

            JSONObject headersJson = new JSONObject(headers);
            String headersJsonString = headersJson.toString();
            requestInterceptor.onResponse(url, statusCode, headersJsonString);
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
