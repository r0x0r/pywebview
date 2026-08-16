import UIKit

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private var webViewController: PyWebViewController?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }

        let controller = PyWebViewController(runtime: EmbeddedPyWebViewRuntime())
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try controller.startPython(entryPoint: "python/app/main.py")
            } catch {
                NSLog("pywebview iOS runtime is not available yet: %@", String(describing: error))
            }
        }
        if let frontendURL = Bundle.main.url(
            forResource: "index",
            withExtension: "html",
            subdirectory: "frontend"
        ) {
            let frontendDirectory = frontendURL.deletingLastPathComponent()
            controller.webView.loadFileURL(frontendURL, allowingReadAccessTo: frontendDirectory)
        } else {
            controller.load(html: """
                <!doctype html>
                <html><body><h1>pywebview iOS host</h1>
                <p>The native WKWebView host is running.</p></body></html>
                """)
        }

        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = controller
        self.window = window
        self.webViewController = controller
        window.makeKeyAndVisible()
    }

    func sceneDidEnterBackground(_ scene: UIScene) {
        webViewController?.stopPython()
    }
}
