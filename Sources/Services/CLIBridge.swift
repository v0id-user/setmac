import Foundation
import os.log

private let log = Logger(subsystem: "com.v0id.setmac", category: "CLIBridge")

/// Status and config listings should finish quickly. Installs run as long as they need.
private let quickCommandTimeout: TimeInterval = 120

/// Exit code the CLI uses when an install run finished but some tools failed.
/// The run already reported each failure and a summary, so it is not a crash.
private let exitSomeFailed: Int32 = 2

/// Thread-safe line buffer that parses JSON lines and yields them to an AsyncStream as they arrive.
private final class StreamingLineParser: @unchecked Sendable {
    /// Raw bytes, split on newlines before decoding: a pipe chunk can end in the middle of a
    /// multi-byte character, and decoding chunk by chunk would drop that whole chunk.
    private var buffer = Data()
    private let lock = NSLock()
    private let decoder = JSONDecoder()
    private let continuation: AsyncStream<CLIMessage>.Continuation

    init(continuation: AsyncStream<CLIMessage>.Continuation) {
        self.continuation = continuation
    }

    /// Append raw data from the pipe. Parses and yields complete JSON lines immediately.
    /// Never yields while holding the lock to avoid deadlock with terminationHandler's flush().
    func append(_ chunk: Data) {
        var toYield: [CLIMessage] = []
        lock.lock()
        buffer.append(chunk)
        while let newline = buffer.firstIndex(of: 0x0A) {
            let line = String(decoding: buffer[buffer.startIndex..<newline], as: UTF8.self)
            buffer.removeSubrange(buffer.startIndex...newline)

            guard !line.isEmpty else { continue }
            if let msg = try? decoder.decode(CLIMessage.self, from: Data(line.utf8)) {
                toYield.append(msg)
            } else {
                // Show stray output instead of hiding it in os.log.
                log.warning("Unparseable line: \(line, privacy: .public)")
                toYield.append(CLIMessage(log: line))
            }
        }
        lock.unlock()

        for msg in toYield {
            continuation.yield(msg)
        }
    }

    /// Flush any remaining partial line (called at process exit).
    func flush() {
        lock.lock()
        let remaining = String(decoding: buffer, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
        buffer = Data()
        lock.unlock()

        guard !remaining.isEmpty,
              let msg = try? decoder.decode(CLIMessage.self, from: Data(remaining.utf8))
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
    private var currentProcess: Process?

    /// Stop the running command. The CLI forwards SIGTERM to its installer's process group.
    func cancel() {
        guard let process = currentProcess, process.isRunning else { return }
        log.info("Cancelling CLI pid \(process.processIdentifier)")
        process.terminate()
    }

    func providePassword(_ password: String) {
        guard let handle = stdinHolder.handle else { return }
        let data = (password + "\n").data(using: .utf8) ?? Data()
        handle.write(data)
    }

    func runCommand(_ args: [String], timeout: TimeInterval? = quickCommandTimeout) -> AsyncStream<CLIMessage> {
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
                let cwd = devRepoRoot.path
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

                let cancelled = proc.terminationReason == .uncaughtSignal || proc.terminationStatus == 128 + SIGTERM
                if cancelled {
                    continuation.yield(CLIMessage(log: "Cancelled"))
                } else if proc.terminationStatus != 0 && proc.terminationStatus != exitSomeFailed {
                    let stderrStr = String(data: stderrData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                    let errorMsg = stderrStr.isEmpty
                        ? "CLI process exited with code \(proc.terminationStatus)"
                        : stderrStr
                    continuation.yield(CLIMessage(type: "error", message: errorMsg))
                }

                continuation.finish()
            }

            do {
                try process.run()
                log.info("CLI process launched (pid: \(process.processIdentifier))")
            } catch {
                log.error("Failed to launch CLI: \(error.localizedDescription, privacy: .public)")
                continuation.yield(CLIMessage(type: "error", message: "Failed to launch CLI: \(error.localizedDescription)"))
                continuation.finish()
                return
            }

            currentProcess = process

            if let timeout {
                DispatchQueue.global().asyncAfter(deadline: .now() + timeout) {
                    if process.isRunning {
                        log.error("CLI timed out after \(timeout, privacy: .public)s, killing pid \(process.processIdentifier)")
                        process.terminate()
                    }
                }
            }
        }
    }
}
