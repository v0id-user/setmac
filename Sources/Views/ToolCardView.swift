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

                Text(tool.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.tail)

                statusLine
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
                .help("Installed")

        case .notInstalled:
            Button("Install") {
                onInstall()
            }
            .controlSize(.small)
            .help("Install this tool")

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
                    onInstall()
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

    @ViewBuilder
    private var statusLine: some View {
        switch status {
        case .installed(let version):
            if let v = version {
                Text(v)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }
        case .installing:
            Text("Installing…")
                .font(.caption2)
                .foregroundStyle(.orange)
        case .checking:
            Text("Checking…")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        case .error(let msg):
            Text(msg)
                .font(.caption2)
                .foregroundStyle(.red)
                .lineLimit(1)
                .truncationMode(.tail)
        case .notInstalled, .unknown:
            EmptyView()
        }
    }
}
