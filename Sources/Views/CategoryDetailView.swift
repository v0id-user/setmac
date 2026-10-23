import SwiftUI
struct CategoryDetailView: View {
    let category: ToolCategory
    let state: InstallState
    let bridge: CLIBridge

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
                        onInstall: {
                            Task { await state.run(["install", tool.id], with: bridge) }
                        },
                        disabled: state.isRunning
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
                    Task { await state.run(["install", category.rawValue, "--category"], with: bridge) }
                }
                .disabled(state.isRunning || allInstalled)
                .help("Install all tools in this category")
            }
        }
        .navigationTitle(category.displayName)
    }
}
