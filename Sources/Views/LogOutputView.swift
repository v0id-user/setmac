import SwiftUI

struct LogOutputView: View {
    let lines: [InstallState.LogLine]
    let onClear: () -> Void

    @State private var isCollapsed = false

    var body: some View {
        VStack(spacing: 0) {
            // Header bar
            HStack(spacing: 8) {
                Image(systemName: "terminal")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("Log")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(.secondary)
                Text("(\(lines.count) lines)")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .monospacedDigit()

                Spacer()

                Button {
                    onClear()
                } label: {
                    Image(systemName: "trash")
                        .font(.caption)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("Clear log")
                .disabled(lines.isEmpty)

                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        isCollapsed.toggle()
                    }
                } label: {
                    Image(systemName: isCollapsed ? "chevron.up" : "chevron.down")
                        .font(.caption)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help(isCollapsed ? "Expand log" : "Collapse log")
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.black.opacity(0.6))

            if !isCollapsed {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 2) {
                            ForEach(lines) { line in
                                HStack(alignment: .top, spacing: 8) {
                                    if let tool = line.tool {
                                        Text("[\(tool)]")
                                            .foregroundStyle(.cyan)
                                            .frame(minWidth: 80, alignment: .trailing)
                                    } else {
                                        Text("")
                                            .frame(minWidth: 80)
                                    }
                                    Text(line.message)
                                        .foregroundStyle(.primary)
                                }
                                .font(.system(.caption, design: .monospaced))
                                .id(line.id)
                            }
                        }
                        .padding(8)
                    }
                    .onChange(of: lines.count) {
                        if let last = lines.last {
                            withAnimation {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }
            }
        }
        .background(.black.opacity(0.8), in: .rect(cornerRadius: 8))
    }
}
