import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ConfigsView")

struct ConfigsView: View {
    let state: InstallState
    let bridge: CLIBridge
    @State private var isRunning = false

    private var toolsWithConfigs: [ToolDefinition] {
        state.manifest?.tools.filter { !($0.configs ?? []).isEmpty } ?? []
    }

    var body: some View {
        VStack(spacing: 0) {
            List {
                Section("Dotfiles & Configs") {
                    ForEach(toolsWithConfigs) { tool in
                        ForEach(tool.configs ?? [], id: \.target) { config in
                            HStack {
                                Image(systemName: config.isDir == true ? "folder" : "doc.text")
                                    .foregroundStyle(tool.swiftColor)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(config.source)
                                        .font(.system(.body, design: .monospaced))
                                    Text(tool.name)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }

                                Spacer()

                                Text(config.target)
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                            }
                            .padding(.vertical, 2)
                        }
                    }
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
                Button("Capture Current", systemImage: "arrow.down.doc") {
                    Task { await runConfigsCommand(["configs", "capture"]) }
                }
                .disabled(isRunning)

                Button("Apply Configs", systemImage: "arrow.up.doc") {
                    Task { await runConfigsCommand(["configs", "apply"]) }
                }
                .disabled(isRunning)

                Button("Dry Run", systemImage: "eye") {
                    Task { await runConfigsCommand(["configs", "apply", "--dry-run"]) }
                }
                .disabled(isRunning)
            }
        }
        .navigationTitle("Configs")
    }

    private func runConfigsCommand(_ args: [String]) async {
        log.info("Running configs command: \(args.joined(separator: " "))")
        isRunning = true
        state.isRunning = true
        for await msg in await bridge.runCommand(args) {
            state.applyMessage(msg)
        }
        state.isRunning = false
        isRunning = false
        log.info("Configs command finished: \(args.joined(separator: " "))")
    }
}
