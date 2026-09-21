import AppKit
import Foundation

@MainActor
final class ChapterOneStore: ObservableObject {
    @Published var snapshot: ChapterOneSnapshot?
    @Published var selectedSpirit: String = "thunder"
    @Published var status = "正在读取第一章世界快照..."
    @Published var isRunning = false
    @Published var playerAction = "awaken"
    @Published var playerIntensity = 0.7
    @Published var playerExpression = "玩家进入世界并尝试唤醒眼前之物。"

    static let playerActions = ["ascend", "receive", "flow", "illuminate", "awaken", "adapt", "stabilize", "exchange"]

    init() {
        reload()
    }

    func reload() {
        guard let url = Self.locateSnapshot() else {
            status = "未找到 models/chapter_one_snapshot.json"
            return
        }
        do {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            snapshot = try decoder.decode(ChapterOneSnapshot.self, from: Data(contentsOf: url))
            status = "已载入 \(url.lastPathComponent)"
        } catch {
            status = "快照读取失败：\(error.localizedDescription)"
        }
    }

    func run(offline: Bool) {
        guard !isRunning, let root = Self.locateRepositoryRoot() else { return }
        isRunning = true
        status = offline ? "正在执行确定性第一章规则..." : "正在请求本地 Ollama 决策..."

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        var arguments = [root.appendingPathComponent("tools/run_chapter_one.py").path, "--advance"]
        if offline { arguments.append("--offline") }
        arguments += [
            "--player-action", playerAction,
            "--player-intensity", String(playerIntensity),
            "--player-expression", playerExpression,
        ]
        process.arguments = arguments
        process.currentDirectoryURL = root
        let errorPipe = Pipe()
        process.standardError = errorPipe
        process.terminationHandler = { [weak self] completed in
            let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
            let errorText = String(data: errorData, encoding: .utf8) ?? ""
            Task { @MainActor in
                guard let self else { return }
                self.isRunning = false
                if completed.terminationStatus == 0 {
                    self.reload()
                } else {
                    self.status = "运行失败：\(errorText)"
                }
            }
        }
        do {
            try process.run()
        } catch {
            isRunning = false
            status = "无法启动规则运行时：\(error.localizedDescription)"
        }
    }

    var selected: SpiritSnapshot? {
        snapshot?.spirits.first { $0.slug == selectedSpirit }
    }

    private static func locateSnapshot() -> URL? {
        if let configured = ProcessInfo.processInfo.environment["EDGEWORLD_CHAPTER_ONE_JSON"],
           FileManager.default.fileExists(atPath: configured) {
            return URL(fileURLWithPath: configured)
        }
        return locateRepositoryRoot()?.appendingPathComponent("models/chapter_one_snapshot.json")
    }

    private static func locateRepositoryRoot() -> URL? {
        var current = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        for _ in 0..<10 {
            if FileManager.default.fileExists(atPath: current.appendingPathComponent("tools/run_chapter_one.py").path) {
                return current
            }
            let nested = current.appendingPathComponent("edge-world")
            if FileManager.default.fileExists(atPath: nested.appendingPathComponent("tools/run_chapter_one.py").path) {
                return nested
            }
            current.deleteLastPathComponent()
            if current.path == "/" { break }
        }
        return nil
    }
}
