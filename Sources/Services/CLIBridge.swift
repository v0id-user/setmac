import Foundation

actor CLIBridge {
    private let projectRoot: URL

    init() {
        // In dev mode, project root is the working directory
        // In bundle mode, it's relative to the executable
        if let bundledCLI = Bundle.main.executableURL?
            .deletingLastPathComponent()
            .appendingPathComponent("rig"),
            FileManager.default.fileExists(atPath: bundledCLI.path) {
            projectRoot = Bundle.main.bundleURL
                .appendingPathComponent("Contents")
                .appendingPathComponent("Resources")
        } else {
            // Dev mode: assume we're running from project root
            projectRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        }
    }

    func runCommand(_ args: [String]) -> AsyncStream<CLIMessage> {
        AsyncStream { continuation in
            Task.detached {
                do {
                    let process = Process()
                    let pipe = Pipe()

                    // Try bundled binary first, fall back to uv run
                    let bundledCLI = Bundle.main.executableURL?
                        .deletingLastPathComponent()
                        .appendingPathComponent("rig")

                    if let cli = bundledCLI, FileManager.default.fileExists(atPath: cli.path) {
                        process.executableURL = cli
                        process.arguments = args
                    } else {
                        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
                        process.arguments = ["uv", "run", "--project", "cli", "rig"] + args
                        process.currentDirectoryURL = URL(
                            fileURLWithPath: FileManager.default.currentDirectoryPath
                        )
                    }

                    // Ensure brew and common paths are in PATH
                    var env = ProcessInfo.processInfo.environment
                    let extraPaths = [
                        "/opt/homebrew/bin",
                        "/opt/homebrew/sbin",
                        "/usr/local/bin",
                        NSHomeDirectory() + "/.bun/bin",
                        NSHomeDirectory() + "/.cargo/bin",
                        NSHomeDirectory() + "/.local/bin",
                    ]
                    let currentPath = env["PATH"] ?? "/usr/bin:/bin"
                    env["PATH"] = extraPaths.joined(separator: ":") + ":" + currentPath
                    process.environment = env

                    process.standardOutput = pipe
                    process.standardError = FileHandle.nullDevice

                    try process.run()

                    let handle = pipe.fileHandleForReading
                    var buffer = Data()

                    while true {
                        let chunk = handle.availableData
                        if chunk.isEmpty { break }
                        buffer.append(chunk)

                        // Process complete lines
                        while let newlineRange = buffer.range(of: Data("\n".utf8)) {
                            let lineData = buffer.subdata(in: buffer.startIndex..<newlineRange.lowerBound)
                            buffer.removeSubrange(buffer.startIndex...newlineRange.lowerBound)

                            if let msg = try? JSONDecoder().decode(CLIMessage.self, from: lineData) {
                                continuation.yield(msg)
                            }
                        }
                    }

                    process.waitUntilExit()
                } catch {
                    continuation.yield(CLIMessage(
                        type: "error",
                        tool: nil,
                        message: "CLI bridge error: \(error.localizedDescription)",
                        status: "error",
                        version: nil
                    ))
                }
                continuation.finish()
            }
        }
    }

    func checkAllStatuses() -> AsyncStream<CLIMessage> {
        runCommand(["status"])
    }

    func install(toolId: String) -> AsyncStream<CLIMessage> {
        runCommand(["install", toolId])
    }

    func installAll() -> AsyncStream<CLIMessage> {
        runCommand(["install", "all"])
    }

    func installCategory(_ category: String) -> AsyncStream<CLIMessage> {
        runCommand(["install", category, "--category"])
    }
}
