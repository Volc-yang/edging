import AppKit
import Foundation
import UniformTypeIdentifiers
import SwiftUI

@MainActor
final class PreviewStore: ObservableObject {
    @Published var model: FourPhase4DFile?
    @Published var liveModel: FourPhase4DFile?
    @Published var statusText: String = "Loading..."
    @Published var colorMode: PreviewColorMode = .primary
    @Published var timeSelection: Int = 0
    @Published var selectedIndex: Int?
    @Published var liveMode: Bool = true
    @Published var liveLayout: LiveCastLayout = .threeD

    private let liveSeed: Int64 = 20260620
    private let liveSubject = "swift-preview"
    private var liveProcess: Process?
    private var liveStdoutPipe: Pipe?
    private var liveStderrPipe: Pipe?
    private var liveOutputBuffer = Data()
    private var staticStatusText: String = "Loading..."
    private var liveStatusText: String = "Starting live stream..."

    init() {
        loadDefaultModel()
        startLiveStream()
    }

    var displayModel: FourPhase4DFile? {
        liveMode ? liveModel ?? model : model
    }

    var focusedTimeStep: Int? {
        timeSelection == 0 ? nil : timeSelection - 1
    }

    func loadDefaultModel() {
        if let url = Self.locateDefaultJSON() {
            load(url: url)
        } else {
            staticStatusText = "Could not find the sample cast JSON."
            updateStatusText()
        }
    }

    func setLiveMode(_ enabled: Bool) {
        guard liveMode != enabled else {
            return
        }
        liveMode = enabled
        if enabled {
            startLiveStream()
        } else {
            stopLiveStream()
            updateStatusText()
        }
    }

    func setLiveLayout(_ layout: LiveCastLayout) {
        guard liveLayout != layout else {
            return
        }
        liveLayout = layout
        if liveMode {
            startLiveStream()
        }
    }

    func restartLiveStream() {
        guard liveMode else {
            return
        }
        startLiveStream()
    }

    func openFilePicker() {
        let panel = NSOpenPanel()
        panel.title = "Choose a cast JSON"
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.json]

        if panel.runModal() == .OK, let url = panel.url {
            load(url: url)
        }
    }

    private func load(url: URL) {
        do {
            let data = try Data(contentsOf: url)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let decoded = try decoder.decode(FourPhase4DFile.self, from: data)
            model = decoded
            selectedIndex = nil
            timeSelection = 0
            staticStatusText = "Loaded \(url.lastPathComponent)"
            updateStatusText()
        } catch {
            staticStatusText = "Load failed: \(error.localizedDescription)"
            updateStatusText()
        }
    }

    private func updateStatusText() {
        statusText = liveMode ? liveStatusText : staticStatusText
    }

    private func startLiveStream() {
        stopLiveStream()

        guard let scriptURL = Self.locateLiveStreamScript() else {
            liveStatusText = "Live stream script not found."
            liveMode = false
            updateStatusText()
            return
        }

        guard let pythonURL = Self.locatePythonInterpreter() else {
            liveStatusText = "Python interpreter not found."
            liveMode = false
            updateStatusText()
            return
        }

        let process = Process()
        process.executableURL = pythonURL
        process.arguments = [
            scriptURL.path,
            "--seed",
            "\(liveSeed)",
            "--subject",
            liveSubject,
            "--fps",
            "100",
            "--layout",
            liveLayout.rawValue,
        ]

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            DispatchQueue.main.async {
                self?.consumeLiveOutput(data)
            }
        }

        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            if let text = String(data: data, encoding: .utf8) {
                let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !trimmed.isEmpty else {
                    return
                }
                DispatchQueue.main.async {
                    self?.liveStatusText = "Live stderr: \(trimmed)"
                    self?.updateStatusText()
                }
            }
        }

        process.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                self?.handleLiveTermination(process)
            }
        }

        do {
            try process.run()
            liveProcess = process
            liveStdoutPipe = stdoutPipe
            liveStderrPipe = stderrPipe
            liveOutputBuffer.removeAll(keepingCapacity: true)
            liveStatusText = "Live \(liveLayout.title) stream running at 100 fps"
            updateStatusText()
        } catch {
            liveStatusText = "Live launch failed: \(error.localizedDescription)"
            liveMode = false
            updateStatusText()
        }
    }

    private func stopLiveStream() {
        guard let process = liveProcess else {
            liveStdoutPipe?.fileHandleForReading.readabilityHandler = nil
            liveStderrPipe?.fileHandleForReading.readabilityHandler = nil
            liveStdoutPipe = nil
            liveStderrPipe = nil
            liveOutputBuffer.removeAll(keepingCapacity: true)
            return
        }

        liveProcess = nil
        liveStdoutPipe?.fileHandleForReading.readabilityHandler = nil
        liveStderrPipe?.fileHandleForReading.readabilityHandler = nil
        liveStdoutPipe = nil
        liveStderrPipe = nil
        liveOutputBuffer.removeAll(keepingCapacity: true)
        process.terminate()
    }

    private func consumeLiveOutput(_ data: Data) {
        liveOutputBuffer.append(data)
        let newline = Data([0x0A])
        while let newlineRange = liveOutputBuffer.firstRange(of: newline) {
            let lineData = Data(liveOutputBuffer[..<newlineRange.lowerBound])
            liveOutputBuffer.removeSubrange(liveOutputBuffer.startIndex..<newlineRange.upperBound)
            guard !lineData.isEmpty else {
                continue
            }

            do {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                let decoded = try decoder.decode(FourPhase4DFile.self, from: lineData)
                liveModel = decoded
                if let frameIndex = decoded.frameIndex {
                    let fps = decoded.fps ?? 100
                    liveStatusText = "Live \(decoded.liveLayout?.title ?? liveLayout.title) frame \(frameIndex) @ \(fps) fps"
                    updateStatusText()
                } else {
                    liveStatusText = "Live \(decoded.liveLayout?.title ?? liveLayout.title) frame received"
                    updateStatusText()
                }
            } catch {
                liveStatusText = "Live decode failed: \(error.localizedDescription)"
                updateStatusText()
            }
        }
    }

    private func handleLiveTermination(_ process: Process) {
        guard liveProcess === process else {
            return
        }
        liveStdoutPipe?.fileHandleForReading.readabilityHandler = nil
        liveStderrPipe?.fileHandleForReading.readabilityHandler = nil
        liveProcess = nil
        liveStdoutPipe = nil
        liveStderrPipe = nil
        liveOutputBuffer.removeAll(keepingCapacity: true)
        liveStatusText = "Live stream exited (\(process.terminationStatus))."
        updateStatusText()
    }

    private static func locateDefaultJSON() -> URL? {
        let fileName = "four_phase_4d_cast_1781927642799684000.json"
        let bundleFileName = "default_cast.json"
        let environment = ProcessInfo.processInfo.environment["EDGEWORLD_CAST_JSON"]
        if let environment, FileManager.default.fileExists(atPath: environment) {
            return URL(fileURLWithPath: environment)
        }

        if let bundleURL = Bundle.main.resourceURL?.appendingPathComponent(bundleFileName),
           FileManager.default.fileExists(atPath: bundleURL.path) {
            return bundleURL
        }

        let start = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        var current = start
        for _ in 0..<10 {
            let modelCandidate = current.appendingPathComponent("models").appendingPathComponent(fileName)
            if FileManager.default.fileExists(atPath: modelCandidate.path) {
                return modelCandidate
            }

            let previewCandidate = current
                .appendingPathComponent("edge-world")
                .appendingPathComponent("models")
                .appendingPathComponent(fileName)
            if FileManager.default.fileExists(atPath: previewCandidate.path) {
                return previewCandidate
            }

            let resourcesCandidate = current
                .appendingPathComponent("preview3d")
                .appendingPathComponent(".artifacts")
                .appendingPathComponent("EdgeWorldPreview3D.app")
                .appendingPathComponent("Contents")
                .appendingPathComponent("Resources")
                .appendingPathComponent(bundleFileName)
            if FileManager.default.fileExists(atPath: resourcesCandidate.path) {
                return resourcesCandidate
            }

            current.deleteLastPathComponent()
            if current.path == "/" {
                break
            }
        }

        return nil
    }

    private static func locateLiveStreamScript() -> URL? {
        let fileName = "live_cast_stream.py"
        let start = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        var current = start
        for _ in 0..<10 {
            let toolsCandidate = current.appendingPathComponent("tools").appendingPathComponent(fileName)
            if FileManager.default.fileExists(atPath: toolsCandidate.path) {
                return toolsCandidate
            }

            let previewCandidate = current
                .appendingPathComponent("edge-world")
                .appendingPathComponent("tools")
                .appendingPathComponent(fileName)
            if FileManager.default.fileExists(atPath: previewCandidate.path) {
                return previewCandidate
            }

            current.deleteLastPathComponent()
            if current.path == "/" {
                break
            }
        }

        return nil
    }

    private static func locatePythonInterpreter() -> URL? {
        let candidates = [
            ProcessInfo.processInfo.environment["EDGEWORLD_PYTHON"],
            "/Users/yangacan/edgeWorld/edge-world/.venv/bin/python3",
            "/Users/yangacan/edgeWorld/edge-world/.venv/bin/python",
            "/usr/bin/python3",
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
        ]

        for candidate in candidates.compactMap({ $0 }) {
            if FileManager.default.fileExists(atPath: candidate) {
                return URL(fileURLWithPath: candidate)
            }
        }

        return nil
    }
}
