import Foundation

/// Repo root in dev builds, found from this source file's location so it does not
/// depend on the working directory (launching from Finder sets it to /).
let devRepoRoot: URL = {
    let fromSource = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()  // Services
        .deletingLastPathComponent()  // Sources
        .deletingLastPathComponent()  // repo
    if FileManager.default.fileExists(atPath: fromSource.appendingPathComponent("Resources/tools.json").path) {
        return fromSource
    }
    return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
}()

/// The app's tool list comes from `setmac-cli profile show --json` (see InstallState.loadManifest).
/// This turns a decoding failure of that manifest into a precise, readable reason.
enum ManifestLoader {
    /// "missing \"name\" at tools[3]" rather than Foundation's generic message.
    static func describe(_ error: DecodingError) -> String {
        func path(_ codingPath: [CodingKey]) -> String {
            let joined = codingPath.map { key in
                key.intValue.map { "[\($0)]" } ?? ".\(key.stringValue)"
            }.joined()
            return joined.isEmpty ? "the top level" : String(joined.drop(while: { $0 == "." }))
        }
        switch error {
        case .keyNotFound(let key, let context):
            return "missing \"\(key.stringValue)\" at \(path(context.codingPath))"
        case .typeMismatch(_, let context), .valueNotFound(_, let context):
            return "\(context.debugDescription) (at \(path(context.codingPath)))"
        case .dataCorrupted(let context):
            return "\(context.debugDescription) (at \(path(context.codingPath)))"
        @unknown default:
            return error.localizedDescription
        }
    }
}
