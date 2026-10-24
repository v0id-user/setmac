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
                Text("Automates setting up a fresh macOS with all your developer tools, apps, and configs. Reads from a tools.json manifest that defines what to install and how.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Section("Build Info") {
                LabeledContent("Platform", value: "macOS Tahoe 26")
                LabeledContent("Architecture", value: Self.architecture)
                LabeledContent("UI", value: "SwiftUI + Liquid Glass")
                LabeledContent("Backend", value: "Python CLI (uv)")
                LabeledContent("Manifest", value: "tools.json")
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
