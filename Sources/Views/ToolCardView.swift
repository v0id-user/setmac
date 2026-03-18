import SwiftUI

struct ToolCardView: View {
    let tool: ToolDefinition
    let status: ToolStatus
    let onInstall: () -> Void

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
    }

    @ViewBuilder
    private var statusBadge: some View {
        switch status {
        case .installed:
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
                .font(.title3)

        case .notInstalled:
            Button("Install") {
                onInstall()
            }
            .controlSize(.small)

        case .installing, .checking:
            ProgressView()
                .controlSize(.small)

        case .error:
            HStack(spacing: 6) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                Button("Retry") {
                    onInstall()
                }
                .controlSize(.small)
            }

        case .unknown:
            Image(systemName: "questionmark.circle")
                .foregroundStyle(.secondary)
        }
    }
}
