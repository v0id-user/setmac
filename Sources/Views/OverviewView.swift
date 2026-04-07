import SwiftUI

struct OverviewView: View {
    let state: InstallState
    let bridge: CLIBridge
    @Binding var selection: SidebarItem?
    @State private var isInstalling = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 32) {
                heroCard
                    .padding(.horizontal)

                ForEach(state.categories) { category in
                    CategoryRow(
                        category: category,
                        state: state,
                        onSeeAll: { selection = .category(category) },
                        onInstall: { toolId in Task { await install(toolId) } }
                    )
                }

                if !state.logLines.isEmpty {
                    LogOutputView(lines: state.logLines, onClear: { state.clearLogs() })
                        .padding(.horizontal)
                }
            }
            .padding(.vertical)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button("Refresh", systemImage: "arrow.clockwise") {
                    Task { await refresh() }
                }
                .disabled(state.isRunning)
                .help("Refresh tool installation status")
            }
        }
        .navigationTitle("Overview")
    }

    // MARK: - Hero card

    private var heroCard: some View {
        ZStack(alignment: .bottomLeading) {
            // Background gradient
            LinearGradient(
                colors: [
                    Color(red: 0.13, green: 0.22, blue: 0.82),
                    Color(red: 0.38, green: 0.18, blue: 0.78)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            // Decorative circles
            Circle()
                .fill(.white.opacity(0.06))
                .frame(width: 220)
                .offset(x: 340, y: -50)
            Circle()
                .fill(.white.opacity(0.04))
                .frame(width: 140)
                .offset(x: 460, y: 30)

            HStack(alignment: .bottom, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    if let manifest = state.manifest {
                        Text(manifest.name)
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundStyle(.white)
                        Text(manifest.description)
                            .font(.subheadline)
                            .foregroundStyle(.white.opacity(0.72))
                            .lineLimit(2)
                    }

                    Spacer().frame(height: 6)

                    HStack(spacing: 10) {
                        ProgressView(
                            value: Double(state.installedCount),
                            total: Double(max(state.totalTools, 1))
                        )
                        .tint(.white)
                        .frame(maxWidth: 160)

                        Text("\(state.installedCount) / \(state.totalTools)")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.white.opacity(0.8))

                        if state.isRunning {
                            ProgressView()
                                .controlSize(.mini)
                                .tint(.white)
                        }
                    }
                }

                Spacer()

                Button {
                    Task { await installAll() }
                } label: {
                    Label("Install All", systemImage: "arrow.down.circle.fill")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 9)
                        .background(.white.opacity(0.18), in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(isInstalling || state.installedCount == state.totalTools)
            }
            .padding(24)
        }
        .frame(maxWidth: .infinity)
        .frame(height: 178)
        .clipShape(RoundedRectangle(cornerRadius: 20))
        .shadow(color: .blue.opacity(0.28), radius: 20, y: 6)
    }

    // MARK: - Actions

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

// MARK: - Category row

private struct CategoryRow: View {
    let category: ToolCategory
    let state: InstallState
    let onSeeAll: () -> Void
    let onInstall: (String) -> Void

    private var tools: [ToolDefinition] {
        state.toolsForCategory(category)
    }

    private var installedCount: Int {
        tools.filter { state.status(for: $0.id).isInstalled }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Section header
            HStack(alignment: .firstTextBaseline) {
                Image(systemName: category.icon)
                    .foregroundStyle(category.color)
                    .font(.callout)
                Text(category.displayName)
                    .font(.title3)
                    .fontWeight(.bold)
                Text("·  \(installedCount)/\(tools.count)")
                    .font(.subheadline)
                    .foregroundStyle(.tertiary)
                    .monospacedDigit()
                Spacer()
                Button("See All", action: onSeeAll)
                    .font(.subheadline)
                    .foregroundStyle(.blue)
                    .buttonStyle(.plain)
            }
            .padding(.horizontal)

            // Horizontal scroll of cards
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(tools) { tool in
                        AppStoreToolCard(
                            tool: tool,
                            status: state.status(for: tool.id),
                            onInstall: { onInstall(tool.id) }
                        )
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 4)
            }
        }
    }
}
