import SwiftUI

/// App Store–style square card used in grids and horizontal scroll rows.
struct AppStoreToolCard: View {
    let tool: ToolDefinition
    let status: ToolStatus
    let onInstall: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Icon tile
            ZStack {
                RoundedRectangle(cornerRadius: 14)
                    .fill(tool.swiftColor.opacity(0.12))
                    .frame(height: 72)
                Image(systemName: tool.icon)
                    .font(.system(size: 28, weight: .medium))
                    .foregroundStyle(tool.swiftColor)
            }

            Spacer().frame(height: 10)

            Text(tool.name)
                .font(.subheadline)
                .fontWeight(.semibold)
                .lineLimit(1)

            Text(tool.description)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)
                .frame(minHeight: 28, alignment: .topLeading)

            Spacer().frame(height: 10)

            HStack {
                Spacer()
                actionButton
            }
        }
        .padding(12)
        .frame(width: 140)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 2)
    }

    @ViewBuilder
    private var actionButton: some View {
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
                .frame(height: 22)

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
            Color.clear.frame(height: 22)
        }
    }
}
