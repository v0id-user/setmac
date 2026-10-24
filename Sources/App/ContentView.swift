import SwiftUI
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "ContentView")

struct ContentView: View {
    @State private var selectedItem: SidebarItem? = .overview
    @State private var state = InstallState()
    @State private var bridge = CLIBridge()
    @State private var errorMessage: String?
    @State private var showFirstRun = false

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
                DetailView(item: item, state: state, bridge: bridge, useProfile: useProfile)
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
        .sheet(isPresented: $showFirstRun) {
            FirstRunSheet(starters: state.starters) { spec in
                showFirstRun = false
                Task { await useProfile(spec) }
            }
            .interactiveDismissDisabled()
        }
        .sheet(item: Binding(
            get: { state.pendingReview },
            set: { state.pendingReview = $0 }
        )) { review in
            ProfileReviewSheet(
                review: review,
                onTrust: { Task { await trust(review) } },
                onCancel: {
                    state.pendingReview = nil
                    selectedItem = .profile
                }
            )
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
        await state.run(["profile", "list", "--json"], with: bridge, timeout: 120)
        await state.loadManifest(with: bridge)
        if let loadError = state.loadError {
            log.error("Manifest failed to load: \(loadError, privacy: .public)")
            return
        }
        log.info("Manifest loaded: \(state.totalTools, privacy: .public) tools")
        // Status runs the profile's check commands, so it waits for a choice and for trust.
        if state.profileSource == "default" {
            showFirstRun = true
            return
        }
        if !state.profileTrusted {
            await state.run(["profile", "review", "--json"], with: bridge, timeout: 120)
            return
        }
        await refreshStatuses()
        log.info("Status refresh complete: \(state.installedCount, privacy: .public)/\(state.totalTools, privacy: .public) installed")
    }

    /// Make `spec` the active profile, then reload everything for it.
    private func useProfile(_ spec: String) async {
        await state.run(["profile", "use", spec], with: bridge, timeout: 300)
        if let error = state.lastError {
            errorMessage = error
        }
        await reload()
    }

    /// Trust exactly the reviewed content, then carry on loading.
    private func trust(_ review: ProfileReview) async {
        state.pendingReview = nil
        guard let hash = review.contentHash else { return }
        await state.run(["profile", "trust", review.spec, "--hash", hash], with: bridge, timeout: 120)
        await reload()
    }

    private func refreshStatuses() async {
        await state.run(["status"], with: bridge, timeout: 120)
        if let error = state.lastError {
            log.error("Status check error: \(error, privacy: .public)")
            errorMessage = error
        }
    }
}
