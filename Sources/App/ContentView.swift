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
        } detail: {
            if let item = selectedItem {
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
            state.manifest = ManifestLoader.load()
            log.info("Manifest loaded: \(state.totalTools, privacy: .public) tools")
            log.info("Starting status refresh...")
            await refreshStatuses()
            log.info("Status refresh complete: \(state.installedCount, privacy: .public)/\(state.totalTools, privacy: .public) installed")
        }
        .alert("Error", isPresented: .init(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private func refreshStatuses() async {
        state.isRunning = true
        for await msg in await bridge.checkAllStatuses() {
            if msg.type == "error" {
                log.error("Status check error: \(msg.message ?? "unknown", privacy: .public)")
                errorMessage = msg.message ?? "CLI failed to check tool statuses"
            }
            state.applyMessage(msg)
        }
        state.isRunning = false
    }
}
