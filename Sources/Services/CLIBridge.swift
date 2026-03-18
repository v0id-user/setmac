import Foundation
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "CLIBridge")

private let cliTimeout: TimeInterval = 120

/// Thread-safe line buffer that parses JSON lines and yields them to an AsyncStream as they arrive.
private final class StreamingLineParser: @unchecked Sendable {
    private var buffer = ""
    private let lock = NSLock()
    private let decoder = JSONDecoder()
    private let continuation: AsyncStream<CLIMessage>.Continuation

    init(continuation: AsyncStream<CLIMessage>.Continuation) {
        self.continuation = continuation
    }

    /// Append raw data from the pipe. Parses and yields complete JSON lines immediately.
    /// Never yields while holding the lock to avoid deadlock with terminationHandler's flush().
    func append(_ chunk: Data) {
        guard let text = String(data: chunk, encoding: .utf8) else { return }
        var toYield: [CLIMessage] = []
        lock.lock()
        buffer.append(text)

        // Parse all complete lines
        while let newlineRange = buffer.range(of: "\n") {
            let line = String(buffer[buffer.startIndex..<newlineRange.lowerBound])
            buffer.removeSubrange(buffer.startIndex...newlineRange.lowerBound)

            guard !line.isEmpty,
                  let data = line.data(using: .utf8),
                  let msg = try? decoder.decode(CLIMessage.self, from: data)
            else {
                if !line.isEmpty {
                    log.warning("Unparseable line: \(line, privacy: .public)")
                }
                continue
            }
            toYield.append(msg)
        }
        lock.unlock()

        for msg in toYield {
            continuation.yield(msg)
        }
    }

    /// Flush any remaining partial line (called at process exit).
    func flush() {
        lock.lock()
        let remaining = buffer.trimmingCharacters(in: .whitespacesAndNewlines)
        buffer = ""
        lock.unlock()

        guard !remaining.isEmpty,
              let data = remaining.data(using: .utf8),
              let msg = try? decoder.decode(CLIMessage.self, from: data)
        else {
            if !remaining.isEmpty {
                log.warning("Unparseable trailing data: \(remaining, privacy: .public)")
            }
            return
        }
        continuation.yield(msg)
    }
}

/// Holds the current process's stdin write handle so we can inject the password on auth_required.
private final class StdinHandleHolder: @unchecked Sendable {
    var handle: FileHandle?
}

/// Thread-safe byte accumulator for stderr (not streamed, read at exit).
private final class DataBuffer: @unchecked Sendable {
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
    private let stdinHolder = StdinHandleHolder()

    func providePassword(_ password: String) {
        guard let handle = stdinHolder.handle else { return }
        let data = (password + "\n").data(using: .utf8) ?? Data()
        handle.write(data)
    }

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

            let holder = stdinHolder

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
            // Unbuffer Python output in dev mode (venv/uv) for real-time streaming
            if bundledCLI == nil || !FileManager.default.fileExists(atPath: bundledCLI!.path) {
                env["PYTHONUNBUFFERED"] = "1"
            }
            process.environment = env

            let stdinPipe = Pipe()
            process.standardOutput = stdoutPipe
            process.standardError = stderrPipe
            process.standardInput = stdinPipe
            holder.handle = stdinPipe.fileHandleForWriting

            // Stream stdout: parse JSON lines and yield to UI as they arrive
            let parser = StreamingLineParser(continuation: continuation)
            let stderrBuffer = DataBuffer()

            // Parse and yield on a background queue to avoid blocking the main RunLoop.
            // The handler can run on the main thread; yield blocks until the consumer takes the value.
            // If we block the main thread, the MainActor consumer can't run — deadlock.
            let parseQueue = DispatchQueue(label: "com.v0id.setmac.cli-parse", qos: .userInitiated)
            stdoutPipe.fileHandleForReading.readabilityHandler = { handle in
                let chunk = handle.availableData
                if !chunk.isEmpty {
                    parseQueue.async {
                        parser.append(chunk)
                    }
                }
            }

            stderrPipe.fileHandleForReading.readabilityHandler = { handle in
                let chunk = handle.availableData
                if !chunk.isEmpty {
                    stderrBuffer.append(chunk)
                }
            }

            process.terminationHandler = { proc in
                // Drain remaining stdout before stopping handlers (avoids losing last chunks)
                let stdoutHandle = stdoutPipe.fileHandleForReading
                var data: Data
                repeat {
                    data = stdoutHandle.availableData
                    if !data.isEmpty {
                        parser.append(data)
                    }
                } while !data.isEmpty

                stdoutPipe.fileHandleForReading.readabilityHandler = nil
                stderrPipe.fileHandleForReading.readabilityHandler = nil
                holder.handle = nil
                try? stdinPipe.fileHandleForWriting.close()
                try? stdoutPipe.fileHandleForWriting.close()
                try? stderrPipe.fileHandleForWriting.close()

                // Flush any remaining partial line
                parser.flush()

                let stderrData = stderrBuffer.finalize()
                if let stderrStr = String(data: stderrData, encoding: .utf8), !stderrStr.isEmpty {
                    log.error("CLI stderr:\n\(stderrStr, privacy: .public)")
                }

                log.info("CLI exited with code \(proc.terminationStatus, privacy: .public)")

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
                        version: nil,
                        source: nil,
                        target: nil
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
                    version: nil,
                    source: nil,
                    target: nil
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
