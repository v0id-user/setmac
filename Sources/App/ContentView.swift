import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ContentView")

struct ContentView: View {
    @State private var selectedItem: SidebarItem? = .overview
    @State private var state = InstallState()
    @State private var bridge = CLIBridge()
    @State private var errorMessage: String?

    var body: some View {
        NavigationSplitView {
            SidebarView(selection: $selectedItem, state: state)
                .navigationSplitViewColumnWidth(min: 200, ideal: 240, max: 300)
        } detail: {
            if let loadError = state.loadError {
                ContentUnavailableView {
                    Label("Couldn't Load the Tool List", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(loadError)
                } actions: {
                    Button("Retry") { Task { await reload() } }
                        .disabled(state.isRunning)
                }
            } else if let item = selectedItem {
                DetailView(item: item, state: state, bridge: bridge)
            } else {
                ContentUnavailableView(
                    "Select a Category",
                    systemImage: "sidebar.left",
                    description: Text("Choose an item from the sidebar.")
                )
            }
        }
        .task {
            log.info("App launched, loading manifest...")
            await reload()
        }
        .alert("Error", isPresented: .init(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
        .sheet(item: Binding(
            get: { state.pendingAuthRequest },
            set: { state.pendingAuthRequest = $0 }
        )) { request in
            AuthPasswordSheetView(
                request: request,
                onSubmit: { state.fulfillAuthRequest($0) },
                onCancel: { state.fulfillAuthRequest("") }
            )
        }
    }

    /// Load the manifest from scratch and, if it loads, check every tool's status.
    private func reload() async {
        state.reset()
        await state.loadManifest(with: bridge)
        if let loadError = state.loadError {
            log.error("Manifest failed to load: \(loadError, privacy: .public)")
            return
        }
        log.info("Manifest loaded: \(state.totalTools, privacy: .public) tools")
        await refreshStatuses()
        log.info("Status refresh complete: \(state.installedCount, privacy: .public)/\(state.totalTools, privacy: .public) installed")
    }

    private func refreshStatuses() async {
        await state.run(["status"], with: bridge, timeout: 120)
        if let error = state.lastError {
            log.error("Status check error: \(error, privacy: .public)")
            errorMessage = error
        }
    }
}
