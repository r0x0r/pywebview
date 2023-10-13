package com.pywebview;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.util.Log;
import android.view.View.OnClickListener;
import android.view.Window;
import android.webkit.JsResult;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceResponse;
import android.webkit.WebResourceRequest;
import java.io.BufferedInputStream;
import java.io.InputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.net.URLConnection;
import java.util.List;
import java.util.HashMap;
import java.util.Map;



public class PyWebViewClient extends WebViewClient {
    private EventCallbackWrapper callbackWrapper = null;
    private boolean ignoreSslErrors = false;

    public void setCallback(EventCallbackWrapper callback, boolean ignoreSslErrors) {
        this.callbackWrapper = callback;
        this.ignoreSslErrors = ignoreSslErrors;
    }

    @Override
    public void onPageFinished(WebView view, String url) {
        if (this.callbackWrapper != null) {
            this.callbackWrapper.callback("onPageFinished", url);
        }

        super.onPageFinished(view, url);
    }

    @Override
    public void onReceivedSslError(WebView view, android.webkit.SslErrorHandler handler, android.net.http.SslError error) {
        if (this.ignoreSslErrors) {
            Log.d("PyWebViewClient", "SSL Error: " +error.getPrimaryError());
            handler.proceed();
            return;
        }

        super.onReceivedSslError(view, handler, error);
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        if (request != null && request.getUrl() != null && request.getMethod().equalsIgnoreCase("get")) {
            String scheme = request.getUrl().getScheme().trim();
            if (scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https")) {
                return executeRequest(request.getUrl().toString());
            }
        }
        return null;
    }


    private WebResourceResponse executeRequest(String url) {
        // Retrieve full information about cookies here
        try {
            URL urlObj = new URL(url);
            HttpURLConnection connection = (HttpURLConnection)urlObj.openConnection();
            List<String> cookies  = connection.getHeaderFields().get("Set-Cookie");

            if (cookies != null && cookies.size() > 0) {
                String authority = urlObj.getAuthority();
                String[] urlParts = url.split("://");
                String urlHost = urlParts[0] + "://" + urlParts[1].split("/")[0];

                String cookieString = "{ \"url\": " + "\"" + urlHost + "\", \"cookies\": [";

                for (String entry : cookies) {
                    cookieString += "\"" + entry.replace("\"", "\\\"") + "\",";
                }
                cookieString = cookieString.substring(0, cookieString.length() - 1) + "]}";
                this.callbackWrapper.callback("onCookiesReceived", cookieString);
            }

            return null;

            // TODO: returning null results in a duplicate server request.
            // Figure out how to return the response from the current connection.

            // InputStream in = new BufferedInputStream(connection.getInputStream());
            // String[] contentType = connection.getContentType().split("; ");
            // String encoding = contentType.length > 1 ? contentType[1] : "UTF-8";
            // String mimeType = contentType.length > 0 ? contentType[0] : "text/plain";

            // connection.getHeaderFields();
            // Map<String, String> responseHeaders = new HashMap<>();

            // for (String key : connection.getHeaderFields().keySet()) {
            //     responseHeaders.put(key, connection.getHeaderField(key));
            // }

            // return new WebResourceResponse(mimeType, encoding, connection.getResponseCode(), connection.getResponseMessage(), responseHeaders, in);

        } catch (MalformedURLException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return null;
    }


}


