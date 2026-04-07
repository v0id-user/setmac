import SwiftUI

struct ToolCardView: View {
    let tool: ToolDefinition
    let status: ToolStatus
    let onInstall: (String?) -> Void

    @State private var selectedVersion: String = ""

    var body: some View {
        HStack(spacing: 12) {
            // Icon
            Image(systemName: tool.icon)
                .font(.title2)
                .foregroundStyle(tool.swiftColor)
                .frame(width: 32, height: 32)

            // Info
            VStack(alignment: .leading, spacing: 2) {
                Text(tool.name)
                    .font(.headline)

                Group {
                    switch status {
                    case .installed(let version):
                        if let v = version {
                            Text(v)
                        } else {
                            Text("Installed")
                        }
                    case .notInstalled:
                        Text("Not installed")
                    case .installing:
                        Text("Installing...")
                    case .checking:
                        Text("Checking...")
                    case .error(let msg):
                        Text(msg)
                    case .unknown:
                        Text(tool.description)
                    }
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.tail)
            }

            Spacer()

            // Status indicator + action
            statusBadge
        }
        .padding(.vertical, 4)
        .onAppear {
            if selectedVersion.isEmpty, let def = tool.defaultVersion {
                selectedVersion = def
            }
        }
    }

    @ViewBuilder
    private var statusBadge: some View {
        switch status {
        case .installed:
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
                .font(.title3)
                .help("Installed")

        case .notInstalled:
            HStack(spacing: 6) {
                if let versions = tool.versions, !versions.isEmpty {
                    Picker("Version", selection: $selectedVersion) {
                        ForEach(versions, id: \.self) { v in
                            Text(v).tag(v)
                        }
                    }
                    .pickerStyle(.menu)
                    .labelsHidden()
                    .fixedSize()
                    .help("Select version to install")
                }
                Button("Install") {
                    let version = tool.versions != nil ? selectedVersion : nil
                    onInstall(version.flatMap { $0.isEmpty ? nil : $0 })
                }
                .controlSize(.small)
                .help("Install this tool")
            }

        case .installing, .checking:
            ProgressView()
                .controlSize(.small)
                .help("Installation in progress")

        case .error:
            HStack(spacing: 6) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .help("Installation failed")
                Button("Retry") {
                    let version = tool.versions != nil ? selectedVersion : nil
                    onInstall(version.flatMap { $0.isEmpty ? nil : $0 })
                }
                .controlSize(.small)
                .help("Retry installation")
            }

        case .unknown:
            Image(systemName: "questionmark.circle")
                .foregroundStyle(.secondary)
                .help("Status unknown — refresh to check")
        }
    }
}
