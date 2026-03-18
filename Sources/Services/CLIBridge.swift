import Foundation
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "CLIBridge")

private final class PipeBuffer: @unchecked Sendable {
    private var data = Data()
    private let lock = NSLock()

    func append(_ chunk: Data) {
        lock.lock()
        data.append(chunk)
        lock.unlock()
    }

    func finalize(_ remaining: Data) -> Data {
        lock.lock()
        if !remaining.isEmpty {
            data.append(remaining)
        }
        let result = data
        lock.unlock()
        return result
    }
}

actor CLIBridge {

    func runCommand(_ args: [String]) -> AsyncStream<CLIMessage> {
        AsyncStream { continuation in
            let process = Process()
            let stdoutPipe = Pipe()

            // Try bundled binary first, fall back to uv run
            // Named "setmac-cli" to avoid case-insensitive collision with GUI binary "Setmac"
            let bundledCLI = Bundle.main.executableURL?
                .deletingLastPathComponent()
                .appendingPathComponent("setmac-cli")

            if let cli = bundledCLI, FileManager.default.fileExists(atPath: cli.path) {
                log.info("Using bundled CLI: \(cli.path)")
                process.executableURL = cli
                process.arguments = args
            } else {
                // Dev mode: use uv directly (not /usr/bin/env which may not find it)
                let home = NSHomeDirectory()
                let uvPath = "\(home)/.local/bin/uv"

                if FileManager.default.fileExists(atPath: uvPath) {
                    process.executableURL = URL(fileURLWithPath: uvPath)
                } else {
                    process.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/uv")
                }
                process.arguments = ["run", "--project", "cli", "setmac"] + args
                process.currentDirectoryURL = URL(
                    fileURLWithPath: FileManager.default.currentDirectoryPath
                )
                log.info("Using uv at \(process.executableURL?.path ?? "nil"), cwd: \(process.currentDirectoryURL?.path ?? "nil")")
            }
            log.info("Running: \(process.executableURL?.path ?? "nil") \(args.joined(separator: " "))")

            // Rich PATH for subprocess tools
            var env = ProcessInfo.processInfo.environment
            let home = NSHomeDirectory()
            let extraPaths = [
                "/opt/homebrew/bin",
                "/opt/homebrew/sbin",
                "/usr/local/bin",
                "\(home)/.local/bin",
                "\(home)/.bun/bin",
                "\(home)/.cargo/bin",
            ]
            let currentPath = env["PATH"] ?? "/usr/bin:/bin"
            env["PATH"] = extraPaths.joined(separator: ":") + ":" + currentPath
            process.environment = env

            process.standardOutput = stdoutPipe
            process.standardError = FileHandle.nullDevice
            process.standardInput = FileHandle.nullDevice

            let buffer = PipeBuffer()

            stdoutPipe.fileHandleForReading.readabilityHandler = { handle in
                let chunk = handle.availableData
                if !chunk.isEmpty {
                    buffer.append(chunk)
                }
            }

            process.terminationHandler = { proc in
                stdoutPipe.fileHandleForReading.readabilityHandler = nil

                let remaining = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
                let allData = buffer.finalize(remaining)

                log.info("CLI exited with code \(proc.terminationStatus), received \(allData.count) bytes")

                var parsed = 0
                if let output = String(data: allData, encoding: .utf8) {
                    let decoder = JSONDecoder()
                    for line in output.components(separatedBy: "\n") {
                        guard !line.isEmpty,
                              let lineData = line.data(using: .utf8),
                              let msg = try? decoder.decode(CLIMessage.self, from: lineData)
                        else {
                            if !line.isEmpty {
                                log.warning("Unparseable line: \(line)")
                            }
                            continue
                        }
                        parsed += 1
                        continuation.yield(msg)
                    }
                }
                log.info("Parsed \(parsed) messages")

                continuation.finish()
            }

            do {
                try process.run()
            } catch {
                log.error("Failed to launch CLI: \(error.localizedDescription)")
                continuation.yield(CLIMessage(
                    type: "error",
                    tool: nil,
                    message: "Failed to launch CLI: \(error.localizedDescription)",
                    status: "error",
                    version: nil
                ))
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
