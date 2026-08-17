import Foundation

final class EmbeddedPyWebViewRuntime: PyWebViewRuntime {
    private let runtime = PyWebViewPythonRuntime()

    func start(entryPoint: String) throws {
        try runtime.start(withEntryPoint: entryPoint)
    }

    func handle(message: PyWebViewMessage, reply: @escaping (String, Bool) -> Void) {
        let paramsData = try? JSONEncoder().encode(message.params)
        let paramsJSON = paramsData.flatMap { String(data: $0, encoding: .utf8) } ?? "[]"
        do {
            try runtime.dispatchFunction(
                message.funcName,
                paramsJSON: paramsJSON,
                id: message.id
            )
        } catch {
            reply(error.localizedDescription, true)
        }
    }

    func stop() {
        runtime.stop()
    }
}
