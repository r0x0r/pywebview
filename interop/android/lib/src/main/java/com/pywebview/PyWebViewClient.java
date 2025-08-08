package com.pywebview;

import android.graphics.Bitmap;
import android.net.http.SslError;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.util.Log;

import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONObject;

public class PyWebViewClient extends WebViewClient {
    private volatile EventCallbackWrapper callback;
    private boolean ignoreSslErrors = false;
    private volatile WebViewRequestInterceptor requestInterceptor;
    private Handler mainHandler;
    private volatile boolean isDestroyed = false;

    public PyWebViewClient() {
        super();
        // Initialize handler for main thread to avoid PyJNIus threading issues
        mainHandler = new Handler(Looper.getMainLooper());
    }

    public void setCallback(EventCallbackWrapper callback, boolean ignoreSslErrors) {
        this.callback = callback;
        this.ignoreSslErrors = ignoreSslErrors;
    }

    public void setRequestInterceptor(WebViewRequestInterceptor interceptor) {
        this.requestInterceptor = interceptor;
    }

    public void destroy() {
        isDestroyed = true;
        callback = null;
        requestInterceptor = null;
    }

    /**
     * Safely execute callback on main thread to avoid PyJNIus threading crashes.
     * PyJNIus has issues with concurrent access from multiple threads.
     */
    private void safeCallback(String event, String data) {
        if (isDestroyed) {
            Log.d("python", "Callback skipped - client destroyed: " + event);
            return;
        }

        EventCallbackWrapper currentCallback = callback;
        if (currentCallback == null) {
            Log.d("python", "Callback skipped - no callback set: " + event);
            return;
        }

        if (Looper.myLooper() == Looper.getMainLooper()) {
            // Already on main thread, execute directly
            try {
                currentCallback.callback(event, data);
            } catch (Exception e) {
                Log.e("python", "Error in callback: " + event, e);
                // If we get a JNI error, clear the callback to prevent further crashes
                if (isJniError(e)) {
                    Log.w("python", "JNI error detected, clearing callback to prevent crashes");
                    callback = null;
                }
            }
        } else {
            // Post to main thread
            mainHandler.post(() -> {
                if (isDestroyed) {
                    return;
                }
                EventCallbackWrapper cb = callback;
                if (cb == null) {
                    return;
                }
                try {
                    cb.callback(event, data);
                } catch (Exception e) {
                    Log.e("python", "Error in callback: " + event, e);
                    // If we get a JNI error, clear the callback to prevent further crashes
                    if (isJniError(e)) {
                        Log.w("python", "JNI error detected, clearing callback to prevent crashes");
                        callback = null;
                    }
                }
            });
        }
    }

    /**
     * Safely execute request interceptor calls on main thread
     */
    private String safeOnRequest(String url, String method, String headersJson) {
        if (isDestroyed) {
            return null;
        }

        WebViewRequestInterceptor currentInterceptor = requestInterceptor;
        if (currentInterceptor == null) return null;

        if (Looper.myLooper() == Looper.getMainLooper()) {
            try {
                return currentInterceptor.onRequest(url, method, headersJson);
            } catch (Exception e) {
                Log.e("python", "Error in onRequest", e);
                // If we get a JNI error, clear the interceptor to prevent further crashes
                if (isJniError(e)) {
                    Log.w("python", "JNI error detected, clearing request interceptor to prevent crashes");
                    requestInterceptor = null;
                }
                return null;
            }
        } else {
            // For request interceptor, we need synchronous execution, so we use a blocking approach
            final String[] result = new String[1];
            final Object lock = new Object();

            mainHandler.post(() -> {
                synchronized (lock) {
                    if (isDestroyed) {
                        result[0] = null;
                        lock.notify();
                        return;
                    }
                    WebViewRequestInterceptor interceptor = requestInterceptor;
                    if (interceptor == null) {
                        result[0] = null;
                        lock.notify();
                        return;
                    }
                    try {
                        result[0] = interceptor.onRequest(url, method, headersJson);
                    } catch (Exception e) {
                        Log.e("python", "Error in onRequest", e);
                        // If we get a JNI error, clear the interceptor to prevent further crashes
                        if (isJniError(e)) {
                            Log.w("python", "JNI error detected, clearing request interceptor to prevent crashes");
                            requestInterceptor = null;
                        }
                        result[0] = null;
                    }
                    lock.notify();
                }
            });

            synchronized (lock) {
                try {
                    lock.wait(5000); // 5 second timeout
                } catch (InterruptedException e) {
                    Log.e("python", "Interrupted while waiting for onRequest", e);
                    Thread.currentThread().interrupt();
                }
            }

            return result[0];
        }
    }

    /**
     * Safely execute response interceptor calls on main thread
     */
    private void safeOnResponse(String url, int statusCode, String headersJson) {
        if (isDestroyed) {
            return;
        }

        WebViewRequestInterceptor currentInterceptor = requestInterceptor;
        if (currentInterceptor == null) return;

        if (Looper.myLooper() == Looper.getMainLooper()) {
            try {
                currentInterceptor.onResponse(url, statusCode, headersJson);
            } catch (Exception e) {
                Log.e("python", "Error in onResponse", e);
                // If we get a JNI error, clear the interceptor to prevent further crashes
                if (isJniError(e)) {
                    Log.w("python", "JNI error detected, clearing request interceptor to prevent crashes");
                    requestInterceptor = null;
                }
            }
        } else {
            mainHandler.post(() -> {
                if (isDestroyed) {
                    return;
                }
                WebViewRequestInterceptor interceptor = requestInterceptor;
                if (interceptor == null) {
                    return;
                }
                try {
                    interceptor.onResponse(url, statusCode, headersJson);
                } catch (Exception e) {
                    Log.e("python", "Error in onResponse", e);
                    // If we get a JNI error, clear the interceptor to prevent further crashes
                    if (isJniError(e)) {
                        Log.w("python", "JNI error detected, clearing request interceptor to prevent crashes");
                        requestInterceptor = null;
                    }
                }
            });
        }
    }

    /**
     * Check if an exception is related to JNI errors
     */
    private boolean isJniError(Exception e) {
        String message = e.getMessage();
        return message != null && (
            message.contains("JNI") ||
            message.contains("global reference") ||
            message.contains("stale reference") ||
            message.contains("invalid") ||
            e instanceof IllegalStateException ||
            e instanceof IllegalArgumentException
        );
    }

    @Override
    public void onPageStarted(WebView view, String url, Bitmap favicon) {
        super.onPageStarted(view, url, favicon);
        safeCallback("onPageStarted", url);
    }

    @Override
    public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        safeCallback("onPageFinished", url);
    }

    @Override
    public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
        String errorMsg = "SSL Error for URL: " + error.getUrl() + " - ";
        switch (error.getPrimaryError()) {
            case SslError.SSL_UNTRUSTED:
                errorMsg += "Certificate authority is not trusted";
                break;
            case SslError.SSL_EXPIRED:
                errorMsg += "Certificate has expired";
                break;
            case SslError.SSL_IDMISMATCH:
                errorMsg += "Certificate hostname mismatch";
                break;
            case SslError.SSL_NOTYETVALID:
                errorMsg += "Certificate is not yet valid";
                break;
            case SslError.SSL_DATE_INVALID:
                errorMsg += "Certificate date is invalid";
                break;
            case SslError.SSL_INVALID:
                errorMsg += "Generic certificate error";
                break;
            default:
                errorMsg += "Unknown SSL error: " + error.getPrimaryError();
        }

        if (this.ignoreSslErrors) {
            Log.d("python", errorMsg + " (proceeding due to ignoreSslErrors=true)");
            handler.proceed();
        } else {
            Log.e("python", errorMsg + " (cancelling - ignoreSslErrors=false)");
            handler.cancel();
        }
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        String url = request.getUrl().toString();
        String method = request.getMethod();

        // Collect original request headers
        Map<String, String> headers = new HashMap<>();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && request.getRequestHeaders() != null) {
            headers.putAll(request.getRequestHeaders());
        }

        try {
            String headersJson = new JSONObject(headers).toString();
            String finalHeaders = headersJson;

            // If we have an interceptor, let it modify the headers
            if (requestInterceptor != null) {
                String newHeaders = safeOnRequest(url, method, headersJson);
                if (newHeaders != null) {
                    finalHeaders = newHeaders;
                }
            }

            // Check if this is a cleartext HTTP request to localhost that might be blocked
            if (url.startsWith("http://") && (url.contains("127.0.0.1") || url.contains("localhost"))) {
                Log.w("python", "Skipping custom request for localhost HTTP URL to avoid Network Security Policy issues: " + url);
                // Let the WebView handle this request normally
                return super.shouldInterceptRequest(view, request);
            }

            // Use custom request to ensure we get response headers
            return performCustomRequest(url, method, finalHeaders);

        } catch (Exception e) {
            Log.e("python", "Error processing request", e);

            if (requestInterceptor != null) {
                notifyInterceptorOfError(url, e);
            }
            return super.shouldInterceptRequest(view, request);
        }
    }


    private void processCookies(String url, Map<String, String> responseHeaders) {
        // Process cookies from response headers without making a new connection
        try {
            // Look for Set-Cookie headers (there can be multiple)
            List<String> setCookieHeaders = new ArrayList<>();

            for (Map.Entry<String, String> entry : responseHeaders.entrySet()) {
                if ("Set-Cookie".equalsIgnoreCase(entry.getKey())) {
                    setCookieHeaders.add(entry.getValue());
                }
            }

            // Convert setCookieHeaders to JSON and pass to callback
            if (!setCookieHeaders.isEmpty()) {
                try {
                    JSONObject cookieData = new JSONObject();
                    cookieData.put("url", url);
                    org.json.JSONArray cookieArray = new org.json.JSONArray();
                    for (String cookieHeader : setCookieHeaders) {
                        // Strip "Set-Cookie:" prefix if present
                        String cleanCookie = cookieHeader.replaceFirst("^Set-Cookie:\\s*", "");
                        cookieArray.put(cleanCookie);
                    }
                    cookieData.put("cookies", cookieArray);
                    safeCallback("onCookiesReceived", cookieData.toString());
                } catch (Exception jsonEx) {
                    Log.e("python", "Error creating JSON for cookies", jsonEx);
                }
            }

        } catch (Exception e) {
            Log.e("python", "Error processing cookies", e);
        }
    }

    private WebResourceResponse performCustomRequest(String url, String method, String headersJson) throws Exception {
        // Skip custom requests for certain protocols that can't be handled externally
        if (url.startsWith("data:") || url.startsWith("file:") || url.startsWith("android_asset:") || url.startsWith("android_res:")) {
            Log.d("python", "Skipping custom request for protocol: " + url);
            throw new Exception("Protocol not supported for custom requests");
        }

        JSONObject headersObj = new JSONObject(headersJson);

        // Create and configure connection
        java.net.URL urlObj = new java.net.URL(url);
        java.net.HttpURLConnection connection = (java.net.HttpURLConnection) urlObj.openConnection();

        // Handle SSL for HTTPS connections with self-signed certificates
        if (connection instanceof javax.net.ssl.HttpsURLConnection && ignoreSslErrors) {
            javax.net.ssl.HttpsURLConnection httpsConnection = (javax.net.ssl.HttpsURLConnection) connection;

            try {
                // Create a trust manager that accepts all certificates
                javax.net.ssl.TrustManager[] trustAllCerts = new javax.net.ssl.TrustManager[] {
                    new javax.net.ssl.X509TrustManager() {
                        public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                            return new java.security.cert.X509Certificate[0];
                        }
                        public void checkClientTrusted(java.security.cert.X509Certificate[] certs, String authType) {
                            // Accept all client certificates
                        }
                        public void checkServerTrusted(java.security.cert.X509Certificate[] certs, String authType) {
                            // Accept all server certificates
                        }
                    }
                };

                // Initialize SSL context with trust-all manager
                javax.net.ssl.SSLContext sslContext = null;
                try {
                    sslContext = javax.net.ssl.SSLContext.getInstance("TLS");
                } catch (Exception e) {
                    try {
                        sslContext = javax.net.ssl.SSLContext.getInstance("SSL");
                    } catch (Exception e2) {
                        sslContext = javax.net.ssl.SSLContext.getInstance("TLSv1");
                    }
                }
                sslContext.init(null, trustAllCerts, new java.security.SecureRandom());

                // Apply SSL configuration to HTTPS connection
                httpsConnection.setSSLSocketFactory(sslContext.getSocketFactory());

                // Disable hostname verification for self-signed certificates
                httpsConnection.setHostnameVerifier(new javax.net.ssl.HostnameVerifier() {
                    public boolean verify(String hostname, javax.net.ssl.SSLSession session) {
                        return true; // Accept all hostnames
                    }
                });

            } catch (Exception sslEx) {
                Log.e("python", "Failed to configure SSL context for self-signed cert: " + sslEx.getMessage(), sslEx);
                // Continue anyway - the connection might still work with default SSL settings
            }
        }

        connection.setRequestMethod(method);

        // Set headers
        java.util.Iterator<String> keys = headersObj.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            connection.setRequestProperty(key, headersObj.getString(key));
        }

        // Connect with SSL error handling
        try {
            connection.connect();
        } catch (javax.net.ssl.SSLHandshakeException sslEx) {
            Log.e("python", "SSL handshake failed for URL: " + url + " - " + sslEx.getMessage());
            if (ignoreSslErrors) {
                Log.w("python", "SSL error occurred despite ignoreSslErrors=true. Check SSL configuration.");
            }
            throw sslEx;
        }

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

        // Get response data with error handling
        InputStream inputStream;
        int statusCode;
        String reasonPhrase;

        try {
            statusCode = connection.getResponseCode();
            reasonPhrase = connection.getResponseMessage();

            if (statusCode >= 200 && statusCode < 300) {
                inputStream = connection.getInputStream();
            } else {
                // For error responses, try to get error stream
                inputStream = connection.getErrorStream();
                if (inputStream == null) {
                    inputStream = connection.getInputStream();
                }
            }
        } catch (javax.net.ssl.SSLHandshakeException sslEx) {
            Log.e("python", "SSL handshake failed while reading response from: " + url);
            if (ignoreSslErrors) {
                Log.w("python", "SSL error occurred despite ignoreSslErrors=true. Check SSL configuration.");
            }
            throw sslEx;
        }

        // Collect response headers
        Map<String, String> responseHeaders = new HashMap<>();
        for (Map.Entry<String, List<String>> entry : connection.getHeaderFields().entrySet()) {
            if (entry.getKey() != null && !entry.getValue().isEmpty()) {
                responseHeaders.put(entry.getKey(), entry.getValue().get(0));
            }
        }

        // Notify interceptor
        safeOnResponse(url, statusCode, new JSONObject(responseHeaders).toString());

        // Process cookies from response headers
        processCookies(url, responseHeaders);

        // Return appropriate response based on API level
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            return new WebResourceResponse(mimeType, encoding, statusCode, reasonPhrase, responseHeaders, inputStream);
        } else {
            return new WebResourceResponse(mimeType, encoding, inputStream);
        }
    }

    private void notifyInterceptorOfError(String url, Exception e) {
        if (isDestroyed) {
            return;
        }

        try {
            JSONObject errorInfo = new JSONObject();
            errorInfo.put("error", e.getMessage());
            safeOnResponse(url, 0, errorInfo.toString());
        } catch (Exception jsonEx) {
            Log.e("python", "Error creating JSON for error response", jsonEx);
        }
    }

    @Override
    public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
        super.onReceivedHttpError(view, request, errorResponse);

        if (isDestroyed) {
            return;
        }

        WebViewRequestInterceptor currentInterceptor = requestInterceptor;
        if (currentInterceptor != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            String url = request.getUrl().toString();
            int statusCode = errorResponse.getStatusCode();

            Map<String, String> headers = new HashMap<>();
            if (errorResponse.getResponseHeaders() != null) {
                headers.putAll(errorResponse.getResponseHeaders());
            }

            JSONObject headersJson = new JSONObject(headers);
            String headersJsonString = headersJson.toString();
            safeOnResponse(url, statusCode, headersJsonString);
        }

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

            safeCallback("onReceivedHttpError", data.toString());
        } catch (Exception e) {
                Log.e("python", "Error creating JSON", e);
        }
    }
}

