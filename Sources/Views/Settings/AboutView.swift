import SwiftUI

struct AboutView: View {
    var body: some View {
        Form {
            Section {
                VStack(spacing: 8) {
                    Image(nsImage: NSApp.applicationIconImage)
                        .resizable()
                        .frame(width: 96, height: 96)
                        .accessibilityHidden(true)
                    Text("setmac")
                        .font(.title)
                        .fontWeight(.bold)
                    Text("macOS Setup Automator")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text("Version \(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—")")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
            }

            Section("About") {
                Text("Sets up a Mac from a profile: a starter, or your own profile that picks tools from the public catalog and adds its own apps and dotfiles. Nothing from a profile runs until you have reviewed it, and dotfiles are only replaced when you choose them.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Section("Build Info") {
                LabeledContent("Platform", value: "macOS Tahoe 26")
                LabeledContent("Architecture", value: Self.architecture)
                LabeledContent("UI", value: "SwiftUI + Liquid Glass")
                LabeledContent("Backend", value: "Python CLI (uv)")
                LabeledContent("Tools", value: "Profiles over a public catalog")
            }
        }
        .formStyle(.grouped)
        .navigationTitle("About")
    }

    private static var architecture: String {
        #if arch(arm64)
        "arm64"
        #else
        "x86_64"
        #endif
    }
}
