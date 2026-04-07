import SwiftUI

/// Horizontal list-style card — used in search results and anywhere a row layout is needed.
struct ToolCardView: View {
    let tool: ToolDefinition
    let status: ToolStatus
    let onInstall: () -> Void

    var body: some View {
        HStack(spacing: 14) {
            // Icon tile (App Store search style)
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(tool.swiftColor.opacity(0.12))
                    .frame(width: 48, height: 48)
                Image(systemName: tool.icon)
                    .font(.system(size: 20, weight: .medium))
                    .foregroundStyle(tool.swiftColor)
            }

            // Text stack
            VStack(alignment: .leading, spacing: 2) {
                Text(tool.name)
                    .font(.headline)
                    .lineLimit(1)

                Text(tool.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.tail)

                statusLine
            }

            Spacer()

            actionBadge
        }
        .padding(.vertical, 4)
    }

    // MARK: - Status line (third row, only when meaningful)

    @ViewBuilder
    private var statusLine: some View {
        switch status {
        case .installed(let version):
            if let v = version {
                Text(v)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
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

    // MARK: - Action badge (right side)

    @ViewBuilder
    private var actionBadge: some View {
        switch status {
        case .installed:
            Label("Installed", systemImage: "checkmark")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.green)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(.green.opacity(0.12), in: Capsule())

        case .notInstalled:
            Button("GET", action: onInstall)
                .font(.caption.weight(.bold))
                .foregroundStyle(.blue)
                .padding(.horizontal, 12)
                .padding(.vertical, 4)
                .background(.blue.opacity(0.1), in: Capsule())
                .buttonStyle(.plain)

        case .installing, .checking:
            ProgressView()
                .controlSize(.small)

        case .error:
            Button(action: onInstall) {
                Label("Retry", systemImage: "exclamationmark")
                    .font(.caption2.weight(.bold))
            }
            .foregroundStyle(.red)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(.red.opacity(0.1), in: Capsule())
            .buttonStyle(.plain)

        case .unknown:
            Image(systemName: "questionmark.circle")
                .foregroundStyle(.tertiary)
                .help("Status unknown — refresh to check")
        }
    }
}
