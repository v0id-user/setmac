import Foundation

enum ManifestLoader {
    static func load() -> ToolManifest? {
        // Try bundle resource first
        if let url = Bundle.module.url(forResource: "tools", withExtension: "json") {
            return decode(from: url)
        }

        // Fall back to project root (dev mode)
        let devPath = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("Resources")
            .appendingPathComponent("tools.json")
        if FileManager.default.fileExists(atPath: devPath.path) {
            return decode(from: devPath)
        }

        return nil
    }

    private static func decode(from url: URL) -> ToolManifest? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(ToolManifest.self, from: data)
    }
}
