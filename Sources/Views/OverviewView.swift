import SwiftUI

struct OverviewView: View {
    let state: InstallState
    let bridge: CLIBridge

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header
                headerSection

                // Category summary cards
                LazyVGrid(columns: [
                    GridItem(.adaptive(minimum: 200, maximum: 300), spacing: 16)
                ], spacing: 16) {
                    ForEach(state.categories) { category in
                        CategorySummaryCard(category: category, state: state)
                    }
                }

                if !state.pendingSetupSteps.isEmpty {
                    FinishSetupView(tools: state.pendingSetupSteps)
                }

                // Log output
                if !state.logLines.isEmpty {
                    LogOutputView(lines: state.logLines)
                }
            }
            .padding()
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button("Refresh", systemImage: "arrow.clockwise") {
                    Task { await state.run(["status"], with: bridge, timeout: 120) }
                }
                .disabled(state.isRunning)
                .help("Refresh tool installation status")

                if state.isRunning {
                    Button("Cancel", systemImage: "stop.circle") {
                        Task { await bridge.cancel() }
                    }
                    .help("Stop the running command")
                } else {
                    if !state.lastFailedIds.isEmpty {
                        Button("Retry Failed", systemImage: "arrow.counterclockwise") {
                            Task { await state.run(["install"] + state.lastFailedIds, with: bridge) }
                        }
                        .help("Install only the tools that failed or were skipped")
                    }
                    Button("Install All", systemImage: "arrow.down.circle") {
                        Task { await state.run(["install", "all"], with: bridge) }
                    }
                    .help("Install all tools, then apply dotfiles")
                }
            }
        }
        .navigationTitle("Overview")
    }

    private var headerSection: some View {
        HStack(spacing: 16) {
            // Progress ring
            ZStack {
                Circle()
                    .stroke(.quaternary, lineWidth: 8)
                Circle()
                    .trim(from: 0, to: progress)
                    .stroke(.green, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeInOut, value: progress)
                VStack(spacing: 2) {
                    Text("\(state.installedCount)")
                        .font(.title)
                        .fontWeight(.bold)
                        .monospacedDigit()
                    Text("of \(state.totalTools)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(width: 100, height: 100)

            VStack(alignment: .leading, spacing: 4) {
                if let manifest = state.manifest {
                    Text(manifest.name)
                        .font(.title)
                        .fontWeight(.bold)
                    Text(manifest.description)
                        .foregroundStyle(.secondary)
                }
                if state.isRunning {
                    HStack(spacing: 6) {
                        ProgressView()
                            .controlSize(.small)
                        Text(state.currentTool ?? "Working…")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } else if let summary = state.lastSummary {
                    Label(summary, systemImage: state.lastRunFailed ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(state.lastRunFailed ? .orange : .green)
                        .textSelection(.enabled)
                }
            }

            Spacer()
        }
    }

    private var progress: Double {
        guard state.totalTools > 0 else { return 0 }
        return Double(state.installedCount) / Double(state.totalTools)
    }
}

struct CategorySummaryCard: View {
    let category: ToolCategory
    let state: InstallState

    private var tools: [ToolDefinition] {
        state.toolsForCategory(category)
    }

    private var installed: Int {
        tools.filter { state.status(for: $0.id).isInstalled }.count
    }

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: category.icon)
                        .foregroundStyle(category.color)
                    Text(category.displayName)
                        .font(.headline)
                    Spacer()
                    Text("\(installed)/\(tools.count)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                }

                ProgressView(value: Double(installed), total: Double(max(tools.count, 1)))
                    .tint(installed == tools.count ? .green : .blue)
            }
            .padding(4)
        }
    }
}

/// Manual steps left by tools installed in this session.
struct FinishSetupView: View {
    let tools: [ToolDefinition]

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                Label("Finish setup by hand", systemImage: "hand.raised")
                    .font(.headline)
                ForEach(tools) { tool in
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Image(systemName: tool.icon)
                            .foregroundStyle(tool.swiftColor)
                            .frame(width: 16)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(tool.name).fontWeight(.medium)
                            Text(tool.postInstall ?? "")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(4)
        }
    }
}
