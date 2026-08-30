import Foundation
import WebKit

/// The transport used by the native host to forward a JavaScript API request
/// to the embedded Python runtime.
public struct PyWebViewMessage: Codable {
    public let funcName: String
    public let params: [AnyCodable]
    public let id: String

    public init?(body: Any) {
        guard let object = body as? [String: Any],
              let funcName = object["funcName"] as? String,
              let id = object["id"] as? String,
              let params = object["params"] as? [Any] else {
            return nil
        }

        self.funcName = funcName
        self.params = params.map(AnyCodable.init)
        self.id = id
    }
}

/// A small type-erased JSON value used for bridge messages.
public struct AnyCodable: Codable {
    public let value: Any

    public init(_ value: Any) {
        self.value = value
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let value = try? container.decode(String.self) {
            self.value = value
        } else if let value = try? container.decode(Bool.self) {
            self.value = value
        } else if let value = try? container.decode(Double.self) {
            self.value = value
        } else if let value = try? container.decode([AnyCodable].self) {
            self.value = value.map(\.value)
        } else if let value = try? container.decode([String: AnyCodable].self) {
            self.value = value.mapValues(\.value)
        } else if container.decodeNil() {
            self.value = NSNull()
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unsupported JSON value")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let value as String: try container.encode(value)
        case let value as Bool: try container.encode(value)
        case let value as Int: try container.encode(value)
        case let value as Double: try container.encode(value)
        case let value as [Any]: try container.encode(value.map(AnyCodable.init))
        case let value as [String: Any]: try container.encode(value.mapValues(AnyCodable.init))
        case _ as NSNull: try container.encodeNil()
        default: throw EncodingError.invalidValue(value, .init(codingPath: container.codingPath, debugDescription: "Unsupported JSON value"))
        }
    }
}

public final class PyWebViewBridge: NSObject, WKScriptMessageHandler {
    public typealias MessageHandler = (PyWebViewMessage) -> Void

    private let handler: MessageHandler

    public init(handler: @escaping MessageHandler) {
        self.handler = handler
    }

    public func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "jsBridge", let request = PyWebViewMessage(body: message.body) else {
            return
        }
        handler(request)
    }

    public static func resultScript(function: String, id: String, value: String, isError: Bool) -> String {
        let functionJSON = Self.javascriptString(function)
        let idJSON = Self.javascriptString(id)
        let valueJSON = Self.javascriptString(value)
        return "window.pywebview._returnValuesCallbacks[\(functionJSON)][\(idJSON)]({value:\(valueJSON),isError:\(isError ? "true" : "false")});"
    }

    private static func javascriptString(_ string: String) -> String {
        let data = try! JSONSerialization.data(withJSONObject: [string])
        let encoded = String(data: data, encoding: .utf8)!
        return String(encoded.dropFirst().dropLast())
    }
}
