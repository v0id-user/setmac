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
    var tool: String? = nil
    var message: String? = nil
    var status: String? = nil
    var version: String? = nil
    var source: String? = nil
    var target: String? = nil
    /// Tool ids that failed or were skipped, on `summary` messages.
    var failed: [String]? = nil

    /// A plain log line, for CLI output that is not part of the protocol.
    init(log message: String) {
        self.type = "log"
        self.message = message
    }

    init(type: String, message: String) {
        self.type = type
        self.message = message
    }
}

// MARK: - Observable state

@Observable
final class InstallState {
    var manifest: ToolManifest?
    var statuses: [String: ToolStatus] = [:]
    var logLines: [LogLine] = []
    var isRunning = false
    /// Tool currently being installed, for the progress header.
    var currentTool: String?
    /// Result line of the last install run, e.g. "12 installed, 25 already set up, 1 failed: pier".
    var lastSummary: String?
    var lastRunFailed = false
    /// Tool ids that failed or were skipped in the last install run, for "Retry Failed".
    var lastFailedIds: [String] = []
    /// Tools installed in this session that still need a manual step.
    var pendingSetupSteps: [ToolDefinition] {
        manifest?.tools.filter { justInstalled.contains($0.id) && $0.postInstall != nil } ?? []
    }
    private var justInstalled: Set<String> = []
    /// Most recent error not tied to a tool (CLI crash, launch failure).
    var lastError: String?
    /// Why the manifest could not be loaded; the app shows it instead of an empty UI.
    var loadError: String?

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

    /// Load (or reload) the manifest, recording why it failed instead of leaving it empty.
    func loadManifest() {
        do {
            manifest = try ManifestLoader.load()
            loadError = nil
        } catch {
            manifest = nil
            loadError = error.localizedDescription
        }
    }

    /// Forget everything learned from the CLI, e.g. before reloading the manifest.
    func reset() {
        statuses = [:]
        logLines = []
        currentTool = nil
        lastSummary = nil
        lastRunFailed = false
        lastFailedIds = []
        justInstalled = []
        lastError = nil
        configStatuses = [:]
    }

    /// Categories the manifest defines, or the built-in set when it defines none.
    private var definedCategories: [ToolCategory] {
        manifest?.categories?.map(ToolCategory.init) ?? ToolCategory.builtIn
    }

    func toolsForCategory(_ category: ToolCategory) -> [ToolDefinition] {
        guard let tools = manifest?.tools else { return [] }
        if category == .other {
            let defined = Set(definedCategories.map(\.id))
            return tools.filter { !defined.contains($0.category) }
        }
        return tools.filter { $0.category == category.id }
    }

    /// Categories that have tools, in `order` when given, else in manifest order,
    /// with `Other` last for tools in a category nobody defined.
    var categories: [ToolCategory] {
        guard let manifest else { return [] }
        let defined = Dictionary(definedCategories.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        var seen: [ToolCategory] = []
        var hasOther = false
        for tool in manifest.tools {
            if let category = defined[tool.category] {
                if !seen.contains(category) { seen.append(category) }
            } else {
                hasOther = true
            }
        }
        let ordered = seen.enumerated().sorted { a, b in
            (a.element.order ?? Int.max, a.offset) < (b.element.order ?? Int.max, b.offset)
        }.map(\.element)
        return hasOther ? ordered + [.other] : ordered
    }

    var totalTools: Int {
        manifest?.tools.count ?? 0
    }

    var installedCount: Int {
        statuses.values.filter(\.isInstalled).count
    }

    /// Run a CLI command, applying its output and answering password requests.
    /// Only one command runs at a time; a second call while busy is ignored.
    @MainActor
    func run(_ args: [String], with bridge: CLIBridge, timeout: TimeInterval? = nil) async {
        guard !isRunning else {
            log.warning("Ignoring \(args.joined(separator: " "), privacy: .public): a command is already running")
            return
        }
        isRunning = true
        lastError = nil
        let isInstall = args.first == "install"
        if isInstall {
            lastSummary = nil
            lastRunFailed = false
            lastFailedIds = []
        }
        defer {
            isRunning = false
            currentTool = nil
        }
        for await msg in await bridge.runCommand(args, timeout: timeout) {
            if msg.type == "auth_required" {
                let password = await requestPassword(tool: msg.tool, message: msg.message)
                await bridge.providePassword(password)
            } else {
                applyMessage(msg)
            }
        }
    }

    @MainActor
    private func requestPassword(tool: String?, message: String?) async -> String {
        await withCheckedContinuation { (cont: CheckedContinuation<String, Never>) in
            pendingAuthRequest = AuthRequest(
                tool: tool ?? "",
                message: message ?? "Admin password required for installation"
            )
            pendingAuthContinuation = { cont.resume(returning: $0) }
        }
    }

    @MainActor
    func applyMessage(_ msg: CLIMessage) {
        if msg.type == "error" && msg.tool == nil {
            lastError = msg.message
        }
        if msg.type == "summary" {
            lastSummary = msg.message
            lastFailedIds = msg.failed ?? []
            lastRunFailed = !lastFailedIds.isEmpty
        }

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
                currentTool = msg.message ?? tool
                log.info("\(tool, privacy: .public): installing — \(msg.message ?? "", privacy: .public)")
            case "complete":
                statuses[tool] = .installed(version: msg.version)
                justInstalled.insert(tool)
                log.info("\(tool, privacy: .public): install complete (\(msg.version ?? "", privacy: .public))")
            case "error":
                statuses[tool] = .error(msg.message ?? "Unknown error")
                log.error("\(tool, privacy: .public): error — \(msg.message ?? "Unknown error", privacy: .public)")
            case "log":
                log.info("\(tool, privacy: .public): \(msg.message ?? "", privacy: .public)")
            case "skipped":
                // Follows the tool's error line, which already set its status and message.
                log.info("\(tool, privacy: .public): skipped (\(msg.status ?? "", privacy: .public))")
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
