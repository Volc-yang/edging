import SwiftUI

@main
struct EdgeWorldPreview3DApp: App {
    @StateObject private var store = PreviewStore()

    var body: some Scene {
        WindowGroup {
            ContentView(store: store)
        }
        .windowStyle(.automatic)
    }
}
