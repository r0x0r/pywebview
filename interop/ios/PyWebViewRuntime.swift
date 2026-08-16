import Foundation

/// The native boundary required by the embedded Python interpreter.
///
/// A production implementation will initialize Python from the app bundle
/// and invoke the pywebview entry point. Keeping this protocol independent of
/// Python headers allows the WebKit host to be type-checked before the
/// Python.xcframework is introduced.
public protocol PyWebViewRuntime: AnyObject {
    func start(entryPoint: String) throws
    func handle(message: PyWebViewMessage, reply: @escaping (String, Bool) -> Void)
    func stop()
}

public enum PyWebViewRuntimeError: Error {
    case unavailable
    case startupFailed(String)
}

/// Temporary runtime implementation used by the native host scaffold.
/// It makes the bridge failure explicit rather than silently dropping calls.
public final class UnavailablePyWebViewRuntime: PyWebViewRuntime {
    public init() {}

    public func start(entryPoint: String) throws {
        throw PyWebViewRuntimeError.unavailable
    }

    public func handle(message: PyWebViewMessage, reply: @escaping (String, Bool) -> Void) {
        let error = "The embedded Python runtime is not configured for this iOS host."
        reply(error, true)
    }

    public func stop() {}
}
