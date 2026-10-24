import Foundation
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ManifestLoader")

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

enum ManifestError: LocalizedError {
    case notFound
    case unreadable(URL, String)
    case invalid(URL, String)

    var errorDescription: String? {
        switch self {
        case .notFound:
            "No tools.json was found in the app bundle or the source tree."
        case .unreadable(let url, let reason):
            "Could not read \(url.lastPathComponent): \(reason)"
        case .invalid(let url, let reason):
            "\(url.lastPathComponent) is not a valid manifest: \(reason)"
        }
    }
}

enum ManifestLoader {
    /// The first manifest that decodes. Throws the first candidate's error when none does,
    /// so a broken manifest shows up in the app instead of an empty sidebar.
    static func load() throws -> ToolManifest {
        let urls = manifestCandidateURLs()
        var firstError: Error?
        for url in urls {
            log.info("Loading manifest from: \(url.path, privacy: .public)")
            do {
                let manifest = try decode(from: url)
                log.info("Loaded \(manifest.tools.count) tools from manifest")
                return manifest
            } catch {
                log.error("Failed to load manifest: \(error.localizedDescription, privacy: .public)")
                firstError = firstError ?? error
            }
        }
        throw firstError ?? ManifestError.notFound
    }

    private static func manifestCandidateURLs() -> [URL] {
        var urls: [URL] = []

        if let bundledManifest = Bundle.main.url(forResource: "tools", withExtension: "json") {
            urls.append(bundledManifest)
        }

        let devManifest = devRepoRoot
            .appendingPathComponent("Resources")
            .appendingPathComponent("tools.json")
        if FileManager.default.fileExists(atPath: devManifest.path) {
            urls.append(devManifest)
        }

        return urls
    }

    private static func decode(from url: URL) throws -> ToolManifest {
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            throw ManifestError.unreadable(url, error.localizedDescription)
        }
        do {
            return try JSONDecoder().decode(ToolManifest.self, from: data)
        } catch let error as DecodingError {
            throw ManifestError.invalid(url, describe(error))
        }
    }

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
