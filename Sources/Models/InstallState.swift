import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "InstallState")

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

// MARK: - Auth request (for password prompt)

struct AuthRequest: Identifiable {
    let id = UUID()
    let tool: String
    let message: String
}

enum ConfigStatus: String, Codable {
    case bundled
    case system
    case bundledAndSystem = "bundled+system"
    case missing
}

// MARK: - CLI message (decoded from JSON-line output)

struct CLIMessage: Codable {
    let type: String
    let tool: String?
    let message: String?
    let status: String?
    let version: String?
    let source: String?
    let target: String?
}

// MARK: - Observable state

@Observable
final class InstallState {
    var manifest: ToolManifest?
    var statuses: [String: ToolStatus] = [:]
    var logLines: [LogLine] = []
    var isRunning = false

    /// Shown when CLI emits auth_required; user enters password in sheet.
    var pendingAuthRequest: AuthRequest?
    /// Called with password (or "" for cancel) when user submits/cancels.
    var pendingAuthContinuation: ((String) -> Void)?

    /// Config status keyed by "toolId:target" for bundled/system/missing.
    var configStatuses: [String: ConfigStatus] = [:]

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
                    log.debug("\(tool, privacy: .public): installed (\(msg.version ?? "no version", privacy: .public))")
                } else {
                    statuses[tool] = .notInstalled
                    log.debug("\(tool, privacy: .public): not installed")
                }
            case "progress":
                statuses[tool] = .installing
                log.info("\(tool, privacy: .public): installing — \(msg.message ?? "", privacy: .public)")
            case "complete":
                statuses[tool] = .installed(version: msg.version)
                log.info("\(tool, privacy: .public): install complete (\(msg.version ?? "", privacy: .public))")
            case "error":
                statuses[tool] = .error(msg.message ?? "Unknown error")
                log.error("\(tool, privacy: .public): error — \(msg.message ?? "Unknown error", privacy: .public)")
            case "log":
                log.info("\(tool, privacy: .public): \(msg.message ?? "", privacy: .public)")
            case "config_status":
                if let target = msg.target, let statusStr = msg.status,
                   let status = ConfigStatus(rawValue: statusStr) {
                    configStatuses["\(tool):\(target)"] = status
                }
            default:
                log.warning("Unknown message type '\(msg.type, privacy: .public)' for \(tool, privacy: .public)")
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

    /// Called from password sheet when user submits or cancels.
    func fulfillAuthRequest(_ password: String) {
        pendingAuthContinuation?(password)
        pendingAuthRequest = nil
        pendingAuthContinuation = nil
    }

    func configStatus(toolId: String, target: String) -> ConfigStatus? {
        configStatuses["\(toolId):\(target)"]
    }
}
