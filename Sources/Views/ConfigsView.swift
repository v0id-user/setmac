import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ConfigsView")

struct ConfigsView: View {
    let state: InstallState
    let bridge: CLIBridge
    @State private var hasLoadedStatus = false

    private var toolsWithConfigs: [ToolDefinition] {
        state.manifest?.tools.filter { !($0.configs ?? []).isEmpty } ?? []
    }

    var body: some View {
        VStack(spacing: 0) {
            List {
                Section("Dotfiles & Configs") {
                    ForEach(toolsWithConfigs) { tool in
                        ForEach(tool.configs ?? [], id: \.target) { config in
                            ConfigRowView(
                                tool: tool,
                                config: config,
                                status: state.configStatus(toolId: tool.id, target: config.target)
                            )
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
                .disabled(state.isRunning)
                .help("Copy current dotfiles from system into the bundle")

                Button("Apply Configs", systemImage: "arrow.up.doc") {
                    // The button is the choice: replace every differing file, with backups.
                    Task { await runConfigsCommand(["configs", "apply", "--yes"]) }
                }
                .disabled(state.isRunning)
                .help("Copy bundled configs to system locations")

                Button("Dry Run", systemImage: "eye") {
                    Task { await runConfigsCommand(["configs", "apply", "--dry-run"]) }
                }
                .disabled(state.isRunning)
                .help("Preview what would be copied without making changes")
            }
        }
        .navigationTitle("Dotfiles")
        .task {
            if !hasLoadedStatus {
                await loadConfigStatus()
                hasLoadedStatus = true
            }
        }
    }

    private func loadConfigStatus() async {
        await state.run(["configs", "list"], with: bridge, timeout: 120)
    }

    private func runConfigsCommand(_ args: [String]) async {
        log.info("Running configs command: \(args.joined(separator: " "))")
        await state.run(args, with: bridge, timeout: 120)
        // Refresh config status after capture/apply so the badges match the disk.
        if args.count > 1, ["capture", "apply"].contains(args[1]) {
            await loadConfigStatus()
        }
    }
}

private struct ConfigRowView: View {
    let tool: ToolDefinition
    let config: ConfigSpec
    let status: ConfigStatus?

    var body: some View {
        HStack {
            Image(systemName: config.isDir == true ? "folder" : "doc.text")
                .foregroundStyle(tool.swiftColor)

            VStack(alignment: .leading, spacing: 2) {
                Text(config.source)
                    .font(.system(.body, design: .monospaced))
                Text("\(tool.name) → \(config.target)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            if let status {
                statusBadge(status)
            }
        }
        .padding(.vertical, 2)
    }

    private func statusBadge(_ status: ConfigStatus) -> some View {
        let (label, color): (String, Color) = {
            switch status {
            case .bundledAndSystem: return ("Installed", .green)
            case .bundled: return ("Bundled", .orange)
            case .system: return ("On disk", .blue)
            case .missing: return ("Missing", .red)
            }
        }()
        let helpText: String
        switch status {
        case .bundledAndSystem: helpText = "Config is in bundle and applied to system"
        case .bundled: helpText = "Config is in bundle, not yet applied"
        case .system: helpText = "Config exists on system, not in bundle"
        case .missing: helpText = "Config is neither bundled nor on system"
        }
        return Text(label)
            .font(.caption2)
            .fontWeight(.medium)
            .foregroundStyle(color)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
            .help(helpText)
    }
}
