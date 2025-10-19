package com.pywebview;

/**
 * Interface for intercepting WebView requests and responses.
 */
public interface WebViewRequestInterceptor {
    /**
     * Called when a web request is made.
     *
     * @param url The URL of the request
     * @param method The HTTP method (GET, POST, etc.)
     * @param headersJson JSON string representation of the request headers
     */
    String onRequest(String url, String method, String headersJson);

    /**
     * Called when a response is received.
     *
     * @param url The URL of the request
     * @param statusCode The HTTP status code
     * @param headersJson JSON string representation of the response headers
     */
    void onResponse(String url, int statusCode, String headersJson);
}
