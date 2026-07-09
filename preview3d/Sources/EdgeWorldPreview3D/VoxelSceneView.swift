import AppKit
import SceneKit
import SwiftUI

final class CastSCNView: SCNView {
    var onSelectIndex: ((Int?) -> Void)?

    override func mouseDown(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        let hits = hitTest(point, options: nil)
        if let nodeName = hits.first?.node.name, nodeName.hasPrefix("voxel-"), let index = Int(nodeName.dropFirst(6)) {
            onSelectIndex?(index)
        } else {
            onSelectIndex?(nil)
        }
        super.mouseDown(with: event)
    }
}

struct VoxelSceneView: NSViewRepresentable {
    @ObservedObject var store: PreviewStore

    func makeNSView(context: Context) -> CastSCNView {
        let view = CastSCNView()
        configure(view: view)
        return view
    }

    func updateNSView(_ nsView: CastSCNView, context: Context) {
        nsView.onSelectIndex = { index in
            store.selectedIndex = index
        }

        guard let model = store.model else {
            nsView.scene = VoxelSceneBuilder.makeEmptyScene(message: "Loading sample data...")
            return
        }

        VoxelSceneBuilder.rebuild(
            into: nsView,
            model: model,
            colorMode: store.colorMode,
            focusedTimeStep: store.focusedTimeStep,
            selectedIndex: store.selectedIndex
        )
    }

    private func configure(view: CastSCNView) {
        view.backgroundColor = NSColor(calibratedWhite: 0.08, alpha: 1.0)
        view.allowsCameraControl = true
        view.defaultCameraController.interactionMode = .orbitTurntable
        view.defaultCameraController.inertiaEnabled = true
        view.antialiasingMode = .multisampling4X
        view.isJitteringEnabled = true
        view.showsStatistics = false
        view.autoenablesDefaultLighting = true
    }
}

enum VoxelSceneBuilder {
    private struct SpatialKey: Hashable {
        let x: Int
        let y: Int
        let z: Int
    }

    @MainActor
    static func makeEmptyScene(message: String) -> SCNScene {
        let scene = SCNScene()
        scene.background.contents = NSColor(calibratedWhite: 0.08, alpha: 1.0)

        let cameraNode = SCNNode()
        cameraNode.camera = SCNCamera()
        cameraNode.position = SCNVector3(8, 8, 18)
        scene.rootNode.addChildNode(cameraNode)
        scene.rootNode.addChildNode(lightNode())

        let text = SCNText(string: message, extrusionDepth: 0.0)
        text.font = NSFont.systemFont(ofSize: 1.4, weight: .medium)
        text.flatness = 0.2
        text.firstMaterial?.diffuse.contents = NSColor.white
        let textNode = SCNNode(geometry: text)
        textNode.scale = SCNVector3(0.35, 0.35, 0.35)
        textNode.position = SCNVector3(-4.3, 0.0, 0.0)
        scene.rootNode.addChildNode(textNode)
        return scene
    }

    @MainActor
    static func rebuild(
        into view: SCNView,
        model: FourPhase4DFile,
        colorMode: PreviewColorMode,
        focusedTimeStep: Int?,
        selectedIndex: Int?
    ) {
        if let liveLayout = model.liveLayout {
            rebuildLive(
                into: view,
                model: model,
                liveLayout: liveLayout,
                colorMode: colorMode,
                selectedIndex: selectedIndex
            )
            return
        }

        let scene = SCNScene()
        scene.background.contents = NSColor(calibratedWhite: 0.08, alpha: 1.0)

        let contentNode = SCNNode()
        contentNode.name = "content-root"
        scene.rootNode.addChildNode(contentNode)
        scene.rootNode.addChildNode(lightNode())
        let camera = cameraNode()
        scene.rootNode.addChildNode(camera)
        scene.rootNode.addChildNode(originMarkerNode())

        let spatialSpacing: Float = 1.72
        let temporalSpacing: Float = 0.46
        let spatialOffset: Float = 1.5 * spatialSpacing
        let groupedItems = Dictionary(grouping: model.items) { item in
            SpatialKey(x: item.x, y: item.y, z: item.z)
        }

        for key in groupedItems.keys.sorted(by: spatialSort(_:_:)) {
            let cellNode = SCNNode()
            cellNode.position = SCNVector3(
                Float(key.x) * spatialSpacing - spatialOffset,
                Float(key.y) * spatialSpacing - spatialOffset,
                Float(key.z) * spatialSpacing - spatialOffset
            )
            contentNode.addChildNode(cellNode)

            cellNode.addChildNode(makeTemporalAxisNode(height: CGFloat(temporalSpacing * 3.0)))

            guard let items = groupedItems[key] else {
                continue
            }

            for item in items.sorted(by: { $0.timeStep < $1.timeStep }) {
                let isFocused = focusedTimeStep == nil || focusedTimeStep == item.timeStep
                let alpha: CGFloat = isFocused ? 1.0 : 0.16
                let stateNode = makeTemporalStateNode(
                    item: item,
                    colorMode: colorMode,
                    selectedIndex: selectedIndex,
                    alpha: alpha
                )
                stateNode.position = SCNVector3(0, (Float(item.timeStep) - 1.5) * temporalSpacing, 0)
                cellNode.addChildNode(stateNode)
            }

            let label = makeCellLabel(text: "t0→t3")
            label.position = SCNVector3(0.0, 1.05, 0.0)
            cellNode.addChildNode(label)
        }

        view.scene = scene
        view.pointOfView = camera
    }

    @MainActor
    private static func rebuildLive(
        into view: SCNView,
        model: FourPhase4DFile,
        liveLayout: LiveCastLayout,
        colorMode: PreviewColorMode,
        selectedIndex: Int?
    ) {
        let scene = SCNScene()
        scene.background.contents = NSColor(calibratedWhite: 0.08, alpha: 1.0)

        let contentNode = SCNNode()
        contentNode.name = "content-root"
        scene.rootNode.addChildNode(contentNode)
        scene.rootNode.addChildNode(lightNode())
        let camera = cameraNode(for: liveLayout)
        scene.rootNode.addChildNode(camera)
        scene.rootNode.addChildNode(originMarkerNode())
        scene.rootNode.addChildNode(makeSceneLabel(
            text: "Live \(liveLayout.title) · frame \(model.frameIndex ?? 0) · 100 fps",
            position: SCNVector3(-6.5, 4.8, 0)
        ))

        let spacing: Float
        let xOffset: Float
        let yOffset: Float
        let zOffset: Float

        switch liveLayout {
        case .oneD:
            spacing = 0.62
            xOffset = 31.5 * spacing
            yOffset = 0.0
            zOffset = 0.0
        case .twoD:
            spacing = 1.12
            xOffset = 3.5 * spacing
            yOffset = 3.5 * spacing
            zOffset = 0.0
        case .threeD:
            spacing = 1.48
            xOffset = 1.5 * spacing
            yOffset = 1.5 * spacing
            zOffset = 1.5 * spacing
        }

        for item in model.items.sorted(by: { $0.index < $1.index }) {
            let (x, y, z) = livePosition(for: item, layout: liveLayout)
            let node = makeTemporalStateNode(
                item: item,
                colorMode: colorMode,
                selectedIndex: selectedIndex,
                alpha: 1.0
            )
            node.position = SCNVector3(
                Float(x) * spacing - xOffset,
                Float(y) * spacing - yOffset,
                Float(z) * spacing - zOffset
            )
            contentNode.addChildNode(node)
        }

        view.scene = scene
        view.pointOfView = camera
    }

    private static func makeTemporalStateNode(item: FourPhase4DItem, colorMode: PreviewColorMode, selectedIndex: Int?, alpha: CGFloat) -> SCNNode {
        let node = SCNNode()
        let box = SCNBox(width: 0.42, height: 0.42, length: 0.42, chamferRadius: 0.05)
        let material = SCNMaterial()
        let primaryColor = color(for: item.primaryValue)
        let changedColor = color(for: item.changedValue)
        let baseColor: NSColor

        switch colorMode {
        case .primary:
            baseColor = primaryColor
        case .changed:
            baseColor = changedColor
        case .blended:
            baseColor = mix(primaryColor, changedColor, weight: 0.5)
        }

        material.diffuse.contents = baseColor.withAlphaComponent(alpha)
        material.specular.contents = NSColor.white.withAlphaComponent(0.9)
        material.emission.contents = changedColor.withAlphaComponent(CGFloat(0.12 + Double(item.changeCount) * 0.08))
        material.metalness.contents = 0.18
        material.roughness.contents = 0.35
        box.materials = [material]

        let boxNode = SCNNode(geometry: box)
        boxNode.name = "voxel-\(item.index)"
        node.addChildNode(boxNode)
        node.addChildNode(makeNextTimeBridgeNode(item: item, changedColor: changedColor, alpha: alpha))

        if selectedIndex == item.index {
            node.scale = SCNVector3(1.16, 1.16, 1.16)
            boxNode.geometry?.firstMaterial?.emission.contents = NSColor.systemYellow.withAlphaComponent(0.95)
        }

        return node
    }

    private static func makeNextTimeBridgeNode(item: FourPhase4DItem, changedColor: NSColor, alpha: CGFloat) -> SCNNode {
        let bridge = SCNNode()
        let changeCount = max(0, item.changeCount)
        let bridgeLength = CGFloat(0.12 + min(0.14, Double(changeCount) * 0.025))

        let rod = SCNCylinder(radius: 0.03, height: bridgeLength)
        let rodMaterial = SCNMaterial()
        rodMaterial.diffuse.contents = changedColor.withAlphaComponent(alpha * 0.55)
        rodMaterial.emission.contents = changedColor.withAlphaComponent(alpha * 0.38)
        rodMaterial.specular.contents = NSColor.white.withAlphaComponent(0.8)
        rod.materials = [rodMaterial]

        let rodNode = SCNNode(geometry: rod)
        rodNode.position = SCNVector3(0, Float(0.24 + bridgeLength * 0.5), 0)
        bridge.addChildNode(rodNode)

        let endpoint = SCNSphere(radius: 0.06)
        let endpointMaterial = SCNMaterial()
        endpointMaterial.diffuse.contents = changedColor.withAlphaComponent(alpha * 0.9)
        endpointMaterial.emission.contents = changedColor.withAlphaComponent(alpha * 0.7)
        endpointMaterial.specular.contents = NSColor.white.withAlphaComponent(0.95)
        endpoint.materials = [endpointMaterial]

        let endpointNode = SCNNode(geometry: endpoint)
        endpointNode.position = SCNVector3(0, Float(0.28 + bridgeLength), 0)
        bridge.addChildNode(endpointNode)

        return bridge
    }

    private static func makeTemporalAxisNode(height: CGFloat) -> SCNNode {
        let axis = SCNCylinder(radius: 0.018, height: height)
        let material = SCNMaterial()
        material.diffuse.contents = NSColor(calibratedWhite: 1.0, alpha: 0.08)
        material.emission.contents = NSColor(calibratedWhite: 1.0, alpha: 0.18)
        material.specular.contents = NSColor.white.withAlphaComponent(0.15)
        axis.materials = [material]

        let node = SCNNode(geometry: axis)
        return node
    }

    private static func makeCellLabel(text: String) -> SCNNode {
        let label = SCNText(string: text, extrusionDepth: 0.0)
        label.font = NSFont.systemFont(ofSize: 0.72, weight: .semibold)
        label.flatness = 0.15
        label.firstMaterial?.diffuse.contents = NSColor.systemTeal
        let node = SCNNode(geometry: label)
        node.scale = SCNVector3(0.18, 0.18, 0.18)
        let billboard = SCNBillboardConstraint()
        billboard.freeAxes = .all
        node.constraints = [billboard]
        return node
    }

    private static func cameraNode() -> SCNNode {
        let node = SCNNode()
        node.camera = SCNCamera()
        node.camera?.fieldOfView = 62
        node.position = SCNVector3(12.0, 11.0, 24.0)
        node.look(at: SCNVector3(0.0, 0.0, 0.0))
        return node
    }

    private static func cameraNode(for liveLayout: LiveCastLayout) -> SCNNode {
        let node = SCNNode()
        node.camera = SCNCamera()
        node.camera?.fieldOfView = 58

        switch liveLayout {
        case .oneD:
            node.position = SCNVector3(18.0, 7.0, 58.0)
        case .twoD:
            node.position = SCNVector3(10.5, 10.5, 26.0)
        case .threeD:
            node.position = SCNVector3(12.0, 12.0, 24.0)
        }

        node.look(at: SCNVector3(0.0, 0.0, 0.0))
        return node
    }

    private static func lightNode() -> SCNNode {
        let lightNode = SCNNode()
        lightNode.light = SCNLight()
        lightNode.light?.type = .omni
        lightNode.light?.intensity = 1300
        lightNode.position = SCNVector3(12, 18, 12)

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light?.type = .ambient
        ambient.light?.intensity = 260
        ambient.light?.color = NSColor(calibratedWhite: 0.9, alpha: 1.0)

        let container = SCNNode()
        container.addChildNode(lightNode)
        container.addChildNode(ambient)
        return container
    }

    private static func color(for value: Int) -> NSColor {
        let hue = CGFloat((value % 64)) / 64.0
        return NSColor(calibratedHue: hue, saturation: 0.62, brightness: 0.94, alpha: 1.0)
    }

    private static func originMarkerNode() -> SCNNode {
        let node = SCNNode()

        let sphere = SCNSphere(radius: 0.22)
        let sphereMaterial = SCNMaterial()
        sphereMaterial.diffuse.contents = NSColor.systemYellow
        sphereMaterial.emission.contents = NSColor.systemOrange
        sphere.materials = [sphereMaterial]
        node.addChildNode(SCNNode(geometry: sphere))

        let axisLength: CGFloat = 3.4
        node.addChildNode(axisLine(color: .systemRed, from: SCNVector3(-Float(axisLength), 0, 0), to: SCNVector3(Float(axisLength), 0, 0)))
        node.addChildNode(axisLine(color: .systemGreen, from: SCNVector3(0, -Float(axisLength), 0), to: SCNVector3(0, Float(axisLength), 0)))
        node.addChildNode(axisLine(color: .systemBlue, from: SCNVector3(0, 0, -Float(axisLength)), to: SCNVector3(0, 0, Float(axisLength))))

        return node
    }

    private static func axisLine(color: NSColor, from: SCNVector3, to: SCNVector3) -> SCNNode {
        let source = SCNGeometrySource(vertices: [from, to])
        let element = SCNGeometryElement(indices: [UInt16(0), UInt16(1)], primitiveType: .line)
        let geometry = SCNGeometry(sources: [source], elements: [element])
        let material = SCNMaterial()
        material.diffuse.contents = color
        material.emission.contents = color
        material.isDoubleSided = true
        geometry.materials = [material]
        return SCNNode(geometry: geometry)
    }

    private static func spatialSort(_ lhs: SpatialKey, _ rhs: SpatialKey) -> Bool {
        if lhs.z != rhs.z { return lhs.z < rhs.z }
        if lhs.y != rhs.y { return lhs.y < rhs.y }
        return lhs.x < rhs.x
    }

    private static func livePosition(for item: FourPhase4DItem, layout: LiveCastLayout) -> (Float, Float, Float) {
        switch layout {
        case .oneD:
            return (Float(coordValue(item, at: 0, fallback: item.index)), 0.0, 0.0)
        case .twoD:
            return (Float(coordValue(item, at: 1)), Float(coordValue(item, at: 0)), 0.0)
        case .threeD:
            return (
                Float(coordValue(item, at: 2)),
                Float(coordValue(item, at: 1)),
                Float(coordValue(item, at: 0))
            )
        }
    }

    private static func coordValue(_ item: FourPhase4DItem, at index: Int, fallback: Int = 0) -> Int {
        item.coord.count > index ? item.coord[index] : fallback
    }

    private static func makeSceneLabel(text: String, position: SCNVector3) -> SCNNode {
        let label = SCNText(string: text, extrusionDepth: 0.0)
        label.font = NSFont.systemFont(ofSize: 0.8, weight: .semibold)
        label.flatness = 0.15
        label.firstMaterial?.diffuse.contents = NSColor.white
        let node = SCNNode(geometry: label)
        node.scale = SCNVector3(0.18, 0.18, 0.18)
        node.position = position
        let billboard = SCNBillboardConstraint()
        billboard.freeAxes = .all
        node.constraints = [billboard]
        return node
    }

    private static func mix(_ lhs: NSColor, _ rhs: NSColor, weight: CGFloat) -> NSColor {
        let left = lhs.usingColorSpace(.deviceRGB) ?? lhs
        let right = rhs.usingColorSpace(.deviceRGB) ?? rhs
        let inverse = 1.0 - weight
        return NSColor(
            red: left.redComponent * inverse + right.redComponent * weight,
            green: left.greenComponent * inverse + right.greenComponent * weight,
            blue: left.blueComponent * inverse + right.blueComponent * weight,
            alpha: 1.0
        )
    }
}
