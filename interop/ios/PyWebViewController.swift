import UIKit
import WebKit

/// Minimal native host for the iOS WebView backend.
///
/// The PythonRuntime callback is intentionally injected by the eventual
/// embedded-Python bootstrap. This keeps UIKit/WebKit ownership native while
/// leaving interpreter initialization independent of the view controller.
public final class PyWebViewController: UIViewController, WKNavigationDelegate {
    public let webView: WKWebView
    private let bridge: PyWebViewBridge
    private let runtime: PyWebViewRuntime

    public init(runtime: PyWebViewRuntime) {
        self.runtime = runtime
        let configuration = WKWebViewConfiguration()
        weak var owner: PyWebViewController?
        let messageBridge = PyWebViewBridge(handler: { message in
            runtime.handle(message: message) { value, isError in
                owner?.sendResult(function: message.funcName, id: message.id, value: value, isError: isError)
            }
        })
        self.bridge = messageBridge
        configuration.userContentController.add(messageBridge, name: "jsBridge")
        self.webView = WKWebView(frame: .zero, configuration: configuration)
        super.init(nibName: nil, bundle: nil)
        owner = self
        self.webView.navigationDelegate = self
        registerNativeNotifications()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("PyWebViewController must be created programmatically")
    }

    public override func loadView() {
        view = webView
    }

    private func registerNativeNotifications() {
        let center = NotificationCenter.default
        center.addObserver(self, selector: #selector(handleNativeCreateWindow(_:)), name: NSNotification.Name("PyWebViewIOSCreateWindow"), object: nil)
        center.addObserver(self, selector: #selector(handleNativeLoadURL(_:)), name: NSNotification.Name("PyWebViewIOSLoadURL"), object: nil)
        center.addObserver(self, selector: #selector(handleNativeLoadHTML(_:)), name: NSNotification.Name("PyWebViewIOSLoadHTML"), object: nil)
        center.addObserver(self, selector: #selector(handleNativeEvaluateJS(_:)), name: NSNotification.Name("PyWebViewIOSEvaluateJS"), object: nil)
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    @objc private func handleNativeCreateWindow(_ notification: Notification) {
        guard let title = notification.userInfo?["title"] as? String else { return }
        self.title = title
    }

    @objc private func handleNativeLoadURL(_ notification: Notification) {
        guard let urlString = notification.userInfo?["url"] as? String,
              let url = URL(string: urlString) else { return }
        load(url: url)
    }

    @objc private func handleNativeLoadHTML(_ notification: Notification) {
        guard let html = notification.userInfo?["html"] as? String else { return }
        let baseURL = (notification.userInfo?["baseURI"] as? String).flatMap(URL.init(string:))
        load(html: html, baseURL: baseURL)
    }

    @objc private func handleNativeEvaluateJS(_ notification: Notification) {
        guard let script = notification.userInfo?["script"] as? String else { return }
        let reply = notification.userInfo?["reply"] as? (Any?, Error?) -> Void
        evaluateJavaScript(script) { result in
            switch result {
            case let .success(value):
                reply?(value, nil)
            case let .failure(error):
                reply?(nil, error)
            }
        }
    }

    public func startPython(entryPoint: String) throws {
        try runtime.start(entryPoint: entryPoint)
    }

    public func stopPython() {
        runtime.stop()
    }

    public func load(url: URL) {
        webView.load(URLRequest(url: url))
    }

    public func load(html: String, baseURL: URL? = nil) {
        webView.loadHTMLString(html, baseURL: baseURL)
    }

    public func evaluateJavaScript(_ script: String, completion: @escaping (Result<Any?, Error>) -> Void) {
        webView.evaluateJavaScript(script) { value, error in
            if let error {
                completion(.failure(error))
            } else {
                completion(.success(value))
            }
        }
    }

    public func sendResult(function: String, id: String, value: String, isError: Bool = false) {
        let script = PyWebViewBridge.resultScript(function: function, id: id, value: value, isError: isError)
        webView.evaluateJavaScript(script)
    }
}
