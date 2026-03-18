import SwiftUI

struct AboutView: View {
    var body: some View {
        Form {
            Section {
                VStack(spacing: 8) {
                    Image(systemName: "wrench.and.screwdriver")
                        .font(.system(size: 48))
                        .foregroundStyle(.tint)
                    Text("Rig")
                        .font(.title)
                        .fontWeight(.bold)
                    Text("macOS Setup Automator")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text("Version 1.0.0")
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
                LabeledContent("Architecture", value: "arm64")
                LabeledContent("UI", value: "SwiftUI + Liquid Glass")
                LabeledContent("Backend", value: "Python CLI (uv)")
                LabeledContent("Manifest", value: "tools.json")
            }
        }
        .formStyle(.grouped)
        .navigationTitle("About")
    }
}
