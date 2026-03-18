import SwiftUI

struct SidebarView: View {
    @Binding var selection: SidebarItem?
    let state: InstallState

    var body: some View {
        List(selection: $selection) {
            Section {
                sidebarRow(.overview)
            }

            Section("Tools") {
                ForEach(state.categories) { category in
                    let item = SidebarItem.category(category)
                    HStack {
                        Label {
                            Text(item.title)
                        } icon: {
                            Image(systemName: item.icon)
                                .foregroundStyle(item.iconColor)
                        }

                        Spacer()

                        let tools = state.toolsForCategory(category)
                        let installed = tools.filter { state.status(for: $0.id).isInstalled }.count
                        Text("\(installed)/\(tools.count)")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .monospacedDigit()
                    }
                    .tag(item)
                }
            }

            Section {
                sidebarRow(.configs)
                sidebarRow(.about)
            }
        }
        .navigationTitle("setmac")
    }

    @ViewBuilder
    private func sidebarRow(_ item: SidebarItem) -> some View {
        Label {
            Text(item.title)
        } icon: {
            Image(systemName: item.icon)
                .foregroundStyle(item.iconColor)
        }
        .tag(item)
    }
}
