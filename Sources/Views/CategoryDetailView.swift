import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "CategoryDetail")

struct CategoryDetailView: View {
    let category: ToolCategory
    let state: InstallState
    let bridge: CLIBridge
    @State private var isInstalling = false

    private var tools: [ToolDefinition] {
        state.toolsForCategory(category)
    }

    private var allInstalled: Bool {
        tools.allSatisfy { state.status(for: $0.id).isInstalled }
    }

    var body: some View {
        VStack(spacing: 0) {
            List {
                ForEach(tools) { tool in
                    ToolCardView(
                        tool: tool,
                        status: state.status(for: tool.id),
                        onInstall: { version in
                            Task { await install(tool.id, version: version) }
                        }
                    )
                }
            }

            if !state.logLines.isEmpty {
                Divider()
                LogOutputView(lines: state.logLines)
                    .frame(maxHeight: 200)
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button("Install All", systemImage: "arrow.down.circle") {
                    Task { await installCategory() }
                }
                .disabled(isInstalling || allInstalled)
                .help("Install all tools in this category")
            }
        }
        .navigationTitle(category.displayName)
    }

    private func install(_ toolId: String, version: String? = nil) async {
        log.info("Installing tool: \(toolId)\(version.map { " v\($0)" } ?? "")")
        isInstalling = true
        state.isRunning = true
        for await msg in await bridge.install(toolId: toolId, version: version) {
            await processMessage(msg)
        }
        state.isRunning = false
        isInstalling = false
        log.info("Install finished for: \(toolId)")
    }

    private func installCategory() async {
        log.info("Installing category: \(category.rawValue)")
        isInstalling = true
        state.isRunning = true
        for await msg in await bridge.installCategory(category.rawValue) {
            await processMessage(msg)
        }
        state.isRunning = false
        isInstalling = false
        log.info("Category install finished: \(category.rawValue)")
    }

    private func processMessage(_ msg: CLIMessage) async {
        if msg.type == "auth_required" {
            let password = await withCheckedContinuation { (cont: CheckedContinuation<String, Never>) in
                state.pendingAuthRequest = AuthRequest(
                    tool: msg.tool ?? "",
                    message: msg.message ?? "Admin password required for installation"
                )
                state.pendingAuthContinuation = { cont.resume(returning: $0) }
            }
            await bridge.providePassword(password)
        } else {
            state.applyMessage(msg)
        }
    }
}
