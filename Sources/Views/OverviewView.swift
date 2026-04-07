import SwiftUI

struct OverviewView: View {
    let state: InstallState
    let bridge: CLIBridge
    @Binding var selection: SidebarItem?
    @State private var isInstalling = false

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
                        CategorySummaryCard(category: category, state: state) {
                            selection = .category(category)
                        }
                    }
                }

                // Log output
                if !state.logLines.isEmpty {
                    LogOutputView(lines: state.logLines, onClear: { state.clearLogs() })
                }
            }
            .padding()
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button("Refresh", systemImage: "arrow.clockwise") {
                    Task { await refresh() }
                }
                .disabled(state.isRunning)
                .help("Refresh tool installation status")

                Button("Install All", systemImage: "arrow.down.circle") {
                    Task { await installAll() }
                }
                .disabled(isInstalling || state.installedCount == state.totalTools)
                .help("Install all tools from the manifest")
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
                        Text("Checking tools...")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()
        }
    }

    private var progress: Double {
        guard state.totalTools > 0 else { return 0 }
        return Double(state.installedCount) / Double(state.totalTools)
    }

    private func refresh() async {
        state.isRunning = true
        for await msg in await bridge.checkAllStatuses() {
            state.applyMessage(msg)
        }
        state.isRunning = false
    }

    private func installAll() async {
        isInstalling = true
        state.isRunning = true
        for await msg in await bridge.installAll() {
            await processMessage(msg)
        }
        state.isRunning = false
        isInstalling = false
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

struct CategorySummaryCard: View {
    let category: ToolCategory
    let state: InstallState
    let onTap: () -> Void

    private var tools: [ToolDefinition] {
        state.toolsForCategory(category)
    }

    private var installed: Int {
        tools.filter { state.status(for: $0.id).isInstalled }.count
    }

    private var hasErrors: Bool {
        tools.contains { if case .error = state.status(for: $0.id) { return true }; return false }
    }

    var body: some View {
        Button(action: onTap) {
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Image(systemName: category.icon)
                            .foregroundStyle(category.color)
                        Text(category.displayName)
                            .font(.headline)
                        Spacer()
                        if hasErrors {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                        Text("\(installed)/\(tools.count)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .monospacedDigit()
                    }

                    ProgressView(value: Double(installed), total: Double(max(tools.count, 1)))
                        .tint(installed == tools.count ? .green : hasErrors ? .red : .blue)
                }
                .padding(4)
            }
        }
        .buttonStyle(.plain)
    }
}
