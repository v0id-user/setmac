import SwiftUI

struct ContentView: View {
    @State private var selectedItem: SidebarItem? = .overview
    @State private var state = InstallState()
    @State private var bridge = CLIBridge()

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
            state.manifest = ManifestLoader.load()
            await refreshStatuses()
        }
    }

    private func refreshStatuses() async {
        state.isRunning = true
        for await msg in await bridge.checkAllStatuses() {
            state.applyMessage(msg)
        }
        state.isRunning = false
    }
}
