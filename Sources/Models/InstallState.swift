import SwiftUI

// MARK: - Tool status

enum ToolStatus: Equatable {
    case unknown
    case checking
    case installed(version: String?)
    case notInstalled
    case installing
    case error(String)

    var isInstalled: Bool {
        if case .installed = self { return true }
        return false
    }

    var isBusy: Bool {
        switch self {
        case .checking, .installing: true
        default: false
        }
    }
}

// MARK: - CLI message (decoded from JSON-line output)

struct CLIMessage: Codable {
    let type: String
    let tool: String?
    let message: String?
    let status: String?
    let version: String?
}

// MARK: - Observable state

@Observable
final class InstallState {
    var manifest: ToolManifest?
    var statuses: [String: ToolStatus] = [:]
    var logLines: [LogLine] = []
    var isRunning = false

    struct LogLine: Identifiable {
        let id = UUID()
        let timestamp = Date()
        let tool: String?
        let message: String
    }

    func status(for toolId: String) -> ToolStatus {
        statuses[toolId] ?? .unknown
    }

    func toolsForCategory(_ category: ToolCategory) -> [ToolDefinition] {
        manifest?.tools.filter { $0.category == category.rawValue } ?? []
    }

    var categories: [ToolCategory] {
        guard let manifest else { return [] }
        var seen: [ToolCategory] = []
        for tool in manifest.tools {
            if let cat = ToolCategory(rawValue: tool.category), !seen.contains(cat) {
                seen.append(cat)
            }
        }
        return seen
    }

    var totalTools: Int {
        manifest?.tools.count ?? 0
    }

    var installedCount: Int {
        statuses.values.filter(\.isInstalled).count
    }

    @MainActor
    func applyMessage(_ msg: CLIMessage) {
        if let tool = msg.tool {
            switch msg.type {
            case "status":
                if msg.status == "installed" {
                    statuses[tool] = .installed(version: msg.version)
                } else {
                    statuses[tool] = .notInstalled
                }
            case "progress":
                statuses[tool] = .installing
            case "complete":
                statuses[tool] = .installed(version: msg.version)
            case "error":
                statuses[tool] = .error(msg.message ?? "Unknown error")
            default:
                break
            }
        }

        if let message = msg.message {
            logLines.append(LogLine(tool: msg.tool, message: message))
            // Keep last 500 lines
            if logLines.count > 500 {
                logLines.removeFirst(logLines.count - 500)
            }
        }
    }
}
