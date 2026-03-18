import SwiftUI

struct LogOutputView: View {
    let lines: [InstallState.LogLine]

    var body: some View {
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
            .background(.black.opacity(0.8), in: .rect(cornerRadius: 8))
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
