import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ConfigsView")

/// The active profile's dotfiles. Nothing is replaced unless it is ticked; each row shows
/// how the file on this Mac differs, and Restore puts back what an apply replaced.
struct ConfigsView: View {
    let state: InstallState
    let bridge: CLIBridge
    @State private var selected: Set<String> = []
    @State private var expanded: Set<String> = []
    @State private var showRestore = false

    var body: some View {
        VStack(spacing: 0) {
            if state.configItems.isEmpty {
                ContentUnavailableView(
                    "No Dotfiles",
                    systemImage: "doc.on.doc",
                    description: Text("This profile has no dotfiles. Your own profile can add them with configs on its tools.")
                )
            } else {
                List {
                    Section("Tick the files to apply. Replaced files are backed up.") {
                        ForEach(state.configItems) { item in
                            ConfigItemRow(
                                item: item,
                                isSelected: binding(for: item.id, in: $selected),
                                isExpanded: binding(for: item.id, in: $expanded),
                                diff: state.configDiffs[item.id],
                                loadDiff: { Task { await loadDiff(item.id) } }
                            )
                            .disabled(state.isRunning)
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
                Button("Apply Selected", systemImage: "arrow.up.doc") {
                    let ids = state.configItems.map(\.id).filter(selected.contains)
                    Task { await runAndReload(["configs", "apply", "--only", ids.joined(separator: ","), "--yes"]) }
                }
                .disabled(state.isRunning || selected.isEmpty)
                .help("Copy the ticked files into place, backing up what they replace")

                Button("Restore…", systemImage: "clock.arrow.circlepath") { showRestore = true }
                    .disabled(state.isRunning)
                    .help("Put back files that an apply replaced")

                Button("Capture", systemImage: "arrow.down.doc") {
                    Task { await runAndReload(["configs", "capture"]) }
                }
                .disabled(state.isRunning)
                .help("Copy the files on this Mac into your own profile folder (scanned for secrets first)")
            }
        }
        .navigationTitle("Dotfiles")
        // Reloads (and forgets the ticks) whenever the active profile changes.
        .task(id: state.activeSpec) {
            selected = []
            expanded = []
            await load()
        }
        .sheet(isPresented: $showRestore) {
            RestoreSheet(state: state, bridge: bridge, onDone: {
                showRestore = false
                Task { await load() }
            })
        }
    }

    private func binding(for id: String, in set: Binding<Set<String>>) -> Binding<Bool> {
        Binding(
            get: { set.wrappedValue.contains(id) },
            set: { if $0 { set.wrappedValue.insert(id) } else { set.wrappedValue.remove(id) } }
        )
    }

    private func load() async {
        state.configDiffs = [:]
        await state.run(["configs", "list", "--json"], with: bridge, timeout: 120)
    }

    private func loadDiff(_ id: String) async {
        await state.run(["configs", "diff", id, "--json"], with: bridge, timeout: 120)
    }

    private func runAndReload(_ args: [String]) async {
        log.info("Running configs command: \(args.joined(separator: " "))")
        await state.run(args, with: bridge, timeout: 120)
        selected = []
        await load()
    }
}

private struct ConfigItemRow: View {
    let item: ConfigItem
    @Binding var isSelected: Bool
    @Binding var isExpanded: Bool
    let diff: String?
    let loadDiff: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Toggle("", isOn: $isSelected)
                    .labelsHidden()
                    .disabled(item.status == "identical")
                    .help(item.status == "identical" ? "Already matches the profile" : "Apply this file")
                Image(systemName: item.isDir ? "folder" : "doc.text")
                    .foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.source).font(.system(.body, design: .monospaced))
                    Text("\(item.tool) → \(item.target)").font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                statusBadge
                if item.status == "differs" {
                    Button(isExpanded ? "Hide Diff" : "Diff") {
                        isExpanded.toggle()
                        if isExpanded && diff == nil { loadDiff() }
                    }
                    .buttonStyle(.borderless)
                }
            }
            if isExpanded {
                ScrollView([.horizontal, .vertical]) {
                    Text(diff ?? "Loading…")
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(6)
                }
                .frame(maxHeight: 220)
                .background(.quaternary.opacity(0.4))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }
        }
        .padding(.vertical, 2)
    }

    private var statusBadge: some View {
        let (label, color, help): (String, Color, String) = switch item.status {
        case "identical": ("Matches", .green, "The file on this Mac is the same as the profile's")
        case "differs": ("Differs", .orange, "The file on this Mac differs from the profile's; applying replaces it (with a backup)")
        default: ("Missing", .blue, "Not on this Mac yet; applying creates it")
        }
        return Text(label)
            .font(.caption2)
            .fontWeight(.medium)
            .foregroundStyle(color)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
            .help(help)
    }
}

/// Backups made by apply (and by restore), newest first, each restorable.
private struct RestoreSheet: View {
    let state: InstallState
    let bridge: CLIBridge
    let onDone: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Restore Dotfiles").font(.headline)
            Text("Restoring puts back the files an apply replaced and removes files it created. What is there now is backed up first.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            if state.backups.isEmpty {
                Text("No backups yet.").foregroundStyle(.secondary)
            } else {
                List(state.backups) { backup in
                    HStack {
                        VStack(alignment: .leading) {
                            Text(backup.stamp).font(.system(.body, design: .monospaced))
                            Text(backup.ids.joined(separator: ", ")).font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button("Restore") {
                            Task {
                                await state.run(["configs", "restore", backup.stamp], with: bridge, timeout: 120)
                                onDone()
                            }
                        }
                        .disabled(state.isRunning)
                    }
                }
                .frame(minHeight: 200)
            }
            HStack {
                Spacer()
                Button("Done", action: onDone).keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 520)
        .task { await state.run(["configs", "backups", "--json"], with: bridge, timeout: 120) }
    }
}
