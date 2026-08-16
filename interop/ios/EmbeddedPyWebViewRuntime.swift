import Foundation

final class EmbeddedPyWebViewRuntime: PyWebViewRuntime {
    private let runtime = PyWebViewPythonRuntime()

    func start(entryPoint: String) throws {
        var error: NSError?
        if !runtime.start(withEntryPoint: entryPoint, error: &error) {
            throw error ?? PyWebViewRuntimeError.unavailable
        }
    }

    func handle(message: PyWebViewMessage, reply: @escaping (String, Bool) -> Void) {
        let paramsData = try? JSONEncoder().encode(message.params)
        let paramsJSON = paramsData.flatMap { String(data: $0, encoding: .utf8) } ?? "[]"
        var error: NSError?
        let dispatched = runtime.dispatchFunction(
            message.funcName,
            paramsJSON: paramsJSON,
            id: message.id,
            error: &error
        )
        if !dispatched {
            reply(error?.localizedDescription ?? "Python bridge dispatch failed.", true)
        }
    }

    func stop() {
        runtime.stop()
    }
}
