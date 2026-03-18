import Foundation
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ManifestLoader")

enum ManifestLoader {
    static func load() -> ToolManifest? {
        // Try bundle resource first
        if let url = Bundle.module.url(forResource: "tools", withExtension: "json") {
            log.info("Loading manifest from bundle: \(url.path, privacy: .public)")
            if let manifest = decode(from: url) {
                log.info("Loaded \(manifest.tools.count) tools from manifest")
                return manifest
            }
            log.error("Failed to decode manifest from bundle")
        }

        // Fall back to project root (dev mode)
        let devPath = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("Resources")
            .appendingPathComponent("tools.json")
        if FileManager.default.fileExists(atPath: devPath.path) {
            log.info("Loading manifest from dev path: \(devPath.path, privacy: .public)")
            if let manifest = decode(from: devPath) {
                log.info("Loaded \(manifest.tools.count) tools from manifest")
                return manifest
            }
            log.error("Failed to decode manifest from dev path")
        }

        log.error("No manifest found in bundle or dev path")
        return nil
    }

    private static func decode(from url: URL) -> ToolManifest? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(ToolManifest.self, from: data)
    }
}
