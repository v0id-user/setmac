import SwiftUI

struct DetailView: View {
    let item: SidebarItem
    let state: InstallState
    let bridge: CLIBridge

    var body: some View {
        switch item {
        case .overview:
            OverviewView(state: state, bridge: bridge)
        case .category(let cat):
            CategoryDetailView(category: cat, state: state, bridge: bridge)
        case .configs:
            ConfigsView(state: state, bridge: bridge)
        case .about:
            AboutView()
        }
    }
}
