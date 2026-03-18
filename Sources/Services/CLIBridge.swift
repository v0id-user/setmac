import Foundation

actor CLIBridge {

    func runCommand(_ args: [String]) -> AsyncStream<CLIMessage> {
        AsyncStream { continuation in
            Task.detached {
                do {
                    let process = Process()
                    let stdoutPipe = Pipe()

                    // Try bundled binary first, fall back to uv run
                    let bundledCLI = Bundle.main.executableURL?
                        .deletingLastPathComponent()
                        .appendingPathComponent("setmac")

                    if let cli = bundledCLI, FileManager.default.fileExists(atPath: cli.path) {
                        process.executableURL = cli
                        process.arguments = args
                    } else {
                        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
                        process.arguments = ["uv", "run", "--project", "cli", "setmac"] + args
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
                        NSHomeDirectory() + "/.local/bin",
                        NSHomeDirectory() + "/.bun/bin",
                        NSHomeDirectory() + "/.cargo/bin",
                    ]
                    let currentPath = env["PATH"] ?? "/usr/bin:/bin"
                    env["PATH"] = extraPaths.joined(separator: ":") + ":" + currentPath
                    process.environment = env

                    process.standardOutput = stdoutPipe
                    process.standardError = FileHandle.nullDevice
                    process.standardInput = FileHandle.nullDevice

                    try process.run()

                    // Read stdout line-by-line, parse JSON
                    let handle = stdoutPipe.fileHandleForReading
                    for try await line in handle.bytes.lines {
                        guard !line.isEmpty else { continue }
                        guard let data = line.data(using: .utf8),
                              let msg = try? JSONDecoder().decode(CLIMessage.self, from: data)
                        else { continue }
                        continuation.yield(msg)
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
