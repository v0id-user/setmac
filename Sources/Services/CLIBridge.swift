import Foundation
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "CLIBridge")

private let cliTimeout: TimeInterval = 30

private final class PipeBuffer: @unchecked Sendable {
    private var data = Data()
    private let lock = NSLock()

    func append(_ chunk: Data) {
        lock.lock()
        data.append(chunk)
        lock.unlock()
    }

    func finalize() -> Data {
        lock.lock()
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
            let stderrPipe = Pipe()

            // Try bundled binary first, fall back to uv run
            // Named "setmac-cli" to avoid case-insensitive collision with GUI binary "Setmac"
            let bundledCLI = Bundle.main.executableURL?
                .deletingLastPathComponent()
                .appendingPathComponent("setmac-cli")

            if let cli = bundledCLI, FileManager.default.fileExists(atPath: cli.path) {
                log.info("Using bundled CLI: \(cli.path, privacy: .public)")
                process.executableURL = cli
                process.arguments = args
            } else {
                // Dev mode: run the venv script directly (no uv overhead, no hangs)
                let cwd = FileManager.default.currentDirectoryPath
                let venvScript = "\(cwd)/cli/.venv/bin/setmac"

                if FileManager.default.fileExists(atPath: venvScript) {
                    process.executableURL = URL(fileURLWithPath: venvScript)
                    process.arguments = args
                    log.info("Using venv script: \(venvScript, privacy: .public)")
                } else {
                    // Fallback: use uv if venv not set up yet
                    let home = NSHomeDirectory()
                    let uvPath = "\(home)/.local/bin/uv"
                    if FileManager.default.fileExists(atPath: uvPath) {
                        process.executableURL = URL(fileURLWithPath: uvPath)
                    } else {
                        process.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/uv")
                    }
                    process.arguments = ["run", "--frozen", "--project", "cli", "setmac"] + args
                    log.info("Venv not found, falling back to uv at \(process.executableURL?.path ?? "nil", privacy: .public)")
                }
                process.currentDirectoryURL = URL(fileURLWithPath: cwd)
            }
            let fullCmd = ([process.executableURL?.lastPathComponent ?? "?"] + (process.arguments ?? [])).joined(separator: " ")
            log.info("Running: \(fullCmd, privacy: .public)")

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
            process.standardError = stderrPipe
            process.standardInput = FileHandle.nullDevice

            let stdoutBuffer = PipeBuffer()
            let stderrBuffer = PipeBuffer()

            stdoutPipe.fileHandleForReading.readabilityHandler = { handle in
                let chunk = handle.availableData
                if !chunk.isEmpty {
                    stdoutBuffer.append(chunk)
                }
            }

            stderrPipe.fileHandleForReading.readabilityHandler = { handle in
                let chunk = handle.availableData
                if !chunk.isEmpty {
                    stderrBuffer.append(chunk)
                }
            }

            process.terminationHandler = { proc in
                // Stop handlers FIRST, then close write ends to unblock any reads
                stdoutPipe.fileHandleForReading.readabilityHandler = nil
                stderrPipe.fileHandleForReading.readabilityHandler = nil
                try? stdoutPipe.fileHandleForWriting.close()
                try? stderrPipe.fileHandleForWriting.close()

                let allData = stdoutBuffer.finalize()
                let stderrData = stderrBuffer.finalize()

                if let stderrStr = String(data: stderrData, encoding: .utf8), !stderrStr.isEmpty {
                    log.error("CLI stderr:\n\(stderrStr, privacy: .public)")
                }

                log.info("CLI exited with code \(proc.terminationStatus), received \(allData.count) stdout bytes, \(stderrData.count) stderr bytes")

                var parsed = 0
                if let output = String(data: allData, encoding: .utf8) {
                    let decoder = JSONDecoder()
                    for line in output.components(separatedBy: "\n") {
                        guard !line.isEmpty,
                              let lineData = line.data(using: .utf8),
                              let msg = try? decoder.decode(CLIMessage.self, from: lineData)
                        else {
                            if !line.isEmpty {
                                log.warning("Unparseable line: \(line, privacy: .public)")
                            }
                            continue
                        }
                        parsed += 1
                        continuation.yield(msg)
                    }
                }
                log.info("Parsed \(parsed) messages")

                if proc.terminationStatus != 0 {
                    let stderrStr = String(data: stderrData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                    let errorMsg = stderrStr.isEmpty
                        ? "CLI process exited with code \(proc.terminationStatus)"
                        : stderrStr
                    continuation.yield(CLIMessage(
                        type: "error",
                        tool: nil,
                        message: errorMsg,
                        status: "error",
                        version: nil
                    ))
                }

                continuation.finish()
            }

            do {
                try process.run()
                log.info("CLI process launched (pid: \(process.processIdentifier))")
            } catch {
                log.error("Failed to launch CLI: \(error.localizedDescription, privacy: .public)")
                continuation.yield(CLIMessage(
                    type: "error",
                    tool: nil,
                    message: "Failed to launch CLI: \(error.localizedDescription)",
                    status: "error",
                    version: nil
                ))
                continuation.finish()
                return
            }

            // Timeout — kill the process if it takes too long
            DispatchQueue.global().asyncAfter(deadline: .now() + cliTimeout) {
                if process.isRunning {
                    log.error("CLI timed out after \(cliTimeout, privacy: .public)s, killing pid \(process.processIdentifier)")
                    process.terminate()
                }
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
