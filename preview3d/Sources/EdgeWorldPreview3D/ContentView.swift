import AppKit
import SwiftUI

struct ContentView: View {
    @ObservedObject var store: PreviewStore

    var body: some View {
        HStack(spacing: 0) {
            VoxelSceneView(store: store)
                .frame(minWidth: 900, minHeight: 760)

            Divider()

            sidebar
                .frame(width: 320)
                .padding(20)
        }
        .background(Color(nsColor: NSColor(calibratedWhite: 0.10, alpha: 1.0)))
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("EdgeWorld Preview 3D")
                .font(.system(size: 24, weight: .semibold, design: .rounded))

            Text("1^1 点 · 1^2 面 · 1^3 立方体 · 变卦为下一时刻")
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .foregroundStyle(.secondary)

            Text(store.statusText)
                .font(.system(size: 12, weight: .regular, design: .monospaced))
                .foregroundStyle(.secondary)

            GroupBox("Controls") {
                VStack(alignment: .leading, spacing: 12) {
                    Toggle(
                        "Live 100 fps",
                        isOn: Binding(
                            get: { store.liveMode },
                            set: { store.setLiveMode($0) }
                        )
                    )

                    Picker(
                        "Layout",
                        selection: Binding(
                            get: { store.liveLayout },
                            set: { store.setLiveLayout($0) }
                        )
                    ) {
                        ForEach(LiveCastLayout.allCases) { layout in
                            Text(layout.title).tag(layout)
                        }
                    }
                    .pickerStyle(.segmented)
                    .disabled(!store.liveMode)

                    Picker("Color", selection: $store.colorMode) {
                        ForEach(PreviewColorMode.allCases) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)

                    Picker("时间", selection: $store.timeSelection) {
                        Text("All").tag(0)
                        Text("时0").tag(1)
                        Text("时1").tag(2)
                        Text("时2").tag(3)
                        Text("时3").tag(4)
                    }
                    .pickerStyle(.segmented)

                    HStack {
                        Button("Open JSON") {
                            store.openFilePicker()
                        }

                        Button("Restart Live") {
                            store.restartLiveStream()
                        }
                        .disabled(!store.liveMode)

                        Button("Reset") {
                            store.selectedIndex = nil
                            store.timeSelection = 0
                            store.colorMode = .primary
                        }
                    }
                }
            }

            GroupBox("Selection") {
                if let model = store.displayModel, let index = store.selectedIndex, let item = model.items.first(where: { $0.index == index }) {
                    VStack(alignment: .leading, spacing: 8) {
                        labeledValue("Index", "\(item.index)")
                        labeledValue("Coord", item.coord.map(String.init).joined(separator: ", "))
                        if !model.isLiveLayout {
                            labeledValue("Space", item.spatialCoordText)
                            labeledValue("Time", "时\(item.timeStep)")
                        }
                        labeledValue("Primary", "\(item.primaryName) (\(item.primaryValue))")
                        labeledValue("Next", "\(item.changedName) (\(item.changedValue))")
                        labeledValue("Change Count", "\(item.changeCount)")
                        labeledValue("Changing", item.changingPositions.map(String.init).joined(separator: ", "))
                        labeledValue("Line Values", item.lineValuesBottomToTop.map(String.init).joined(separator: ", "))
                    }
                } else {
                    Text("Click any voxel to inspect its coordinates and next-time cast result.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
            }

            GroupBox("Model") {
                if let model = store.displayModel {
                    VStack(alignment: .leading, spacing: 6) {
                        labeledValue("Seed", "\(model.seed)")
                        labeledValue("Subject", model.subject)
                        labeledValue("Layout", model.isLiveLayout ? "\(model.liveLayout?.title ?? model.dimension) live stream" : "4*4*4 space / 4 time steps")
                        labeledValue("Rule", model.isLiveLayout ? "1^1 点 / 1^2 面 / 1^3 立方体 / 变卦=下一时刻" : "1^1 点 / 1^2 面 / 1^3 立方体 / 变卦=下一时刻")
                        labeledValue("Samples", "\(model.count)")
                        if let frameIndex = model.frameIndex {
                            labeledValue("Frame", "\(frameIndex)")
                        }
                    }
                } else {
                    Text("No model loaded.")
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()
        }
        .foregroundStyle(.primary)
    }

    private func labeledValue(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text(label)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .frame(width: 84, alignment: .leading)
            Text(value)
                .font(.system(size: 12, weight: .regular, design: .monospaced))
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
