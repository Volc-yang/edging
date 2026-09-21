import SwiftUI

@main
struct EdgeWorldChapterOneApp: App {
    @StateObject private var store = ChapterOneStore()

    var body: some Scene {
        WindowGroup {
            ChapterOneView(store: store)
        }
        .defaultSize(width: 1240, height: 780)
    }
}
