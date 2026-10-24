import AppKit
import SwiftUI

/// The active profile, and the starters, folders and git URLs to switch to.
struct ProfileView: View {
    let state: InstallState
    let bridge: CLIBridge
    /// Switches the active profile (`profile use`) and reloads everything.
    let useProfile: (String) async -> Void

    @State private var gitURL = ""

    var body: some View {
        Form {
            Section("Active Profile") {
                LabeledContent("Profile", value: state.manifest?.name ?? state.activeSpec ?? "—")
                LabeledContent("Spec") {
                    Text(state.activeSpec ?? "—").font(.system(.body, design: .monospaced)).textSelection(.enabled)
                }
                LabeledContent("Chosen by", value: sourceDescription)
                LabeledContent("Trust") {
                    Label(state.profileTrusted ? "Trusted" : "Not reviewed",
                          systemImage: state.profileTrusted ? "checkmark.seal" : "exclamationmark.shield")
                        .foregroundStyle(state.profileTrusted ? .green : .orange)
                }
                Button("Review What It Runs…") {
                    Task { await state.run(["profile", "review", "--json"], with: bridge, timeout: 120) }
                }
                .disabled(state.isRunning)
            }

            Section("Starters") {
                ForEach(state.starters) { starter in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(starter.name).font(.headline)
                            Text(starter.description).font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        if starter.name == state.activeSpec {
                            Text("Active").font(.caption).foregroundStyle(.secondary)
                        } else {
                            Button("Use") { Task { await useProfile(starter.name) } }
                                .disabled(state.isRunning)
                        }
                    }
                }
            }

            Section("Your Own Profile") {
                Button("Use a Profile Folder…") {
                    if let path = ProfileFolderPicker.choose() {
                        Task { await useProfile(path) }
                    }
                }
                .disabled(state.isRunning)
                HStack {
                    TextField("Git URL, e.g. git@github.com:you/setmac-profile.git", text: $gitURL)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(.body, design: .monospaced))
                    Button("Use") {
                        let url = gitURL.trimmingCharacters(in: .whitespaces)
                        Task { await useProfile(url) }
                    }
                    .disabled(state.isRunning || gitURL.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                Text("A profile you add runs nothing until you have reviewed and trusted it.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .navigationTitle("Profile")
    }

    private var sourceDescription: String {
        switch state.profileSource {
        case "flag": "the --profile option"
        case "env": "the SETMAC_PROFILE variable"
        case "pointer": "you"
        default: "default (not chosen yet)"
        }
    }
}

enum ProfileFolderPicker {
    /// Ask for a folder that holds a profile.json; nil if cancelled.
    @MainActor
    static func choose() -> String? {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.message = "Choose a folder that contains profile.json"
        panel.prompt = "Use Profile"
        return panel.runModal() == .OK ? panel.url?.path : nil
    }
}

/// Everything a profile runs or writes, with the choice to trust it.
struct ProfileReviewSheet: View {
    let review: ProfileReview
    let onTrust: () -> Void
    let onCancel: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Review This Profile").font(.headline)
            Text("setmac runs nothing from \(review.spec) until you trust it. Read every command below; lines marked ! download and run code in one step.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            ScrollView {
                Text(review.text)
                    .font(.system(.caption, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8)
            }
            .background(.quaternary.opacity(0.4))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            HStack {
                Spacer()
                Button("Not Now", role: .cancel, action: onCancel)
                    .keyboardShortcut(.cancelAction)
                Button("Trust This Profile", action: onTrust)
                    .keyboardShortcut(.defaultAction)
                    .disabled(review.contentHash == nil)
            }
        }
        .padding(20)
        .frame(width: 640, height: 520)
    }
}

/// First launch: choose what this Mac should get before anything is checked or installed.
struct FirstRunSheet: View {
    let starters: [StarterInfo]
    let onChoose: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Choose a Starting Profile").font(.title2).bold()
            Text("A profile decides which tools setmac installs. Pick a starter, or use your own profile folder. You can change it any time under Profile.")
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            ForEach(starters) { starter in
                Button {
                    onChoose(starter.name)
                } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(starter.name).font(.headline)
                        Text(starter.description).font(.caption).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(.bordered)
            }
            HStack {
                Button("Use a Profile Folder…") {
                    if let path = ProfileFolderPicker.choose() { onChoose(path) }
                }
                Spacer()
            }
        }
        .padding(24)
        .frame(width: 480)
    }
}
