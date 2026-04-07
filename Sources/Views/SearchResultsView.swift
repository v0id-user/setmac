import SwiftUI

struct SearchResultsView: View {
    let query: String
    let state: InstallState
    let bridge: CLIBridge

    private var results: [(tool: ToolDefinition, category: ToolCategory)] {
        guard !query.isEmpty else { return [] }
        let q = query.lowercased()
        return state.manifest?.tools.compactMap { tool in
            guard
                tool.name.lowercased().contains(q) ||
                tool.description.lowercased().contains(q) ||
                tool.id.lowercased().contains(q),
                let cat = ToolCategory(rawValue: tool.category)
            else { return nil }
            return (tool, cat)
        } ?? []
    }

    var body: some View {
        Group {
            if results.isEmpty {
                ContentUnavailableView.search(text: query)
            } else {
                List {
                    ForEach(results, id: \.tool.id) { item in
                        ToolCardView(
                            tool: item.tool,
                            status: state.status(for: item.tool.id),
                            onInstall: {
                                Task { await install(item.tool.id) }
                            }
                        )
                        .listRowSeparator(.visible)
                    }
                }
            }
        }
        .navigationTitle("Results for \"\(query)\"")
    }

    private func install(_ toolId: String) async {
        state.isRunning = true
        for await msg in await bridge.install(toolId: toolId) {
            await processMessage(msg)
        }
        state.isRunning = false
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
