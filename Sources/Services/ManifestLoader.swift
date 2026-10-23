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

enum ManifestLoader {
    static func load() -> ToolManifest? {
        for url in manifestCandidateURLs() {
            log.info("Loading manifest from: \(url.path, privacy: .public)")
            if let manifest = decode(from: url) {
                log.info("Loaded \(manifest.tools.count) tools from manifest")
                return manifest
            }
            log.error("Failed to decode manifest from: \(url.path, privacy: .public)")
        }

        log.error("No manifest found in app bundle or dev path")
        return nil
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

    private static func decode(from url: URL) -> ToolManifest? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(ToolManifest.self, from: data)
    }
}
