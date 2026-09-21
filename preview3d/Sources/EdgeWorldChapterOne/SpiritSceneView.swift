import AppKit
import SceneKit
import SwiftUI

final class SpiritSCNView: SCNView {
    var selectSpirit: ((String) -> Void)?

    override func mouseDown(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        if let slug = hitTest(point).compactMap({ $0.node.name }).first(where: { $0.hasPrefix("spirit:") }) {
            selectSpirit?(String(slug.dropFirst("spirit:".count)))
        }
        super.mouseDown(with: event)
    }
}

struct SpiritSceneView: NSViewRepresentable {
    @ObservedObject var store: ChapterOneStore

    func makeNSView(context: Context) -> SpiritSCNView {
        let view = SpiritSCNView()
        view.backgroundColor = NSColor(calibratedRed: 0.025, green: 0.03, blue: 0.04, alpha: 1)
        view.allowsCameraControl = true
        view.defaultCameraController.interactionMode = .orbitTurntable
        view.defaultCameraController.inertiaEnabled = true
        view.antialiasingMode = .multisampling4X
        return view
    }

    func updateNSView(_ view: SpiritSCNView, context: Context) {
        view.selectSpirit = { store.selectedSpirit = $0 }
        view.scene = SpiritSceneBuilder.build(snapshot: store.snapshot, selected: store.selectedSpirit)
        view.pointOfView = view.scene?.rootNode.childNode(withName: "camera", recursively: false)
    }
}

enum SpiritSceneBuilder {
    private static let colors: [String: NSColor] = [
        "heaven": NSColor(calibratedWhite: 0.84, alpha: 1),
        "earth": NSColor(calibratedRed: 0.45, green: 0.68, blue: 0.38, alpha: 1),
        "water": NSColor(calibratedRed: 0.20, green: 0.52, blue: 0.72, alpha: 1),
        "fire": NSColor(calibratedRed: 0.92, green: 0.29, blue: 0.20, alpha: 1),
        "thunder": NSColor(calibratedRed: 0.94, green: 0.73, blue: 0.24, alpha: 1),
        "wind": NSColor(calibratedRed: 0.34, green: 0.72, blue: 0.62, alpha: 1),
        "mountain": NSColor(calibratedWhite: 0.48, alpha: 1),
        "lake": NSColor(calibratedRed: 0.65, green: 0.36, blue: 0.58, alpha: 1),
    ]

    @MainActor
    static func build(snapshot: ChapterOneSnapshot?, selected: String) -> SCNScene {
        let scene = SCNScene()
        scene.background.contents = NSColor(calibratedRed: 0.025, green: 0.03, blue: 0.04, alpha: 1)
        addCameraAndLights(to: scene)
        addCenter(to: scene, integrity: snapshot?.cycle.finalIntegrity ?? 0)

        guard let snapshot else { return scene }
        let radius: Float = 4.3
        for (index, spirit) in snapshot.spirits.enumerated() {
            let angle = Float.pi * 2 * Float(index) / Float(snapshot.spirits.count) - Float.pi / 2
            let controlled = spirit.slug == snapshot.worldResponse.control.targetSpirit
            let node = spiritNode(spirit, selected: spirit.slug == selected, control: controlled ? snapshot.worldResponse.control : nil)
            let verticalOffset = controlled ? Float(snapshot.worldResponse.control.verticalOffset) : 0
            node.position = SCNVector3(cos(angle) * radius, sin(Float(index) * 0.8) * 0.3 + verticalOffset, sin(angle) * radius)
            scene.rootNode.addChildNode(node)
        }
        return scene
    }

    @MainActor
    private static func spiritNode(_ spirit: SpiritSnapshot, selected: Bool, control: WorldControl?) -> SCNNode {
        let root = SCNNode()
        root.name = "spirit:\(spirit.slug)"
        let baseRadius = selected ? 0.68 : 0.54
        let sphere = SCNSphere(radius: baseRadius * CGFloat(control?.scaleMultiplier ?? 1.0))
        sphere.segmentCount = 64
        let material = SCNMaterial()
        let color = colors[spirit.slug] ?? .white
        material.diffuse.contents = color
        material.emission.contents = color.withAlphaComponent(selected ? 0.65 : 0.2)
        material.emission.intensity = CGFloat(control?.emissionMultiplier ?? 1.0)
        material.metalness.contents = 0.2
        material.roughness.contents = 0.28
        sphere.materials = [material]
        let body = SCNNode(geometry: sphere)
        body.name = root.name
        root.addChildNode(body)

        let response = control.map { "\n\($0.effectCn) \(String(format: "%.2f", $0.magnitude))" } ?? ""
        let text = SCNText(string: "\(spirit.symbol) \(spirit.trigramName)\n\(spirit.slug)\(response)", extrusionDepth: 0.01)
        text.font = NSFont.systemFont(ofSize: 0.42, weight: .medium)
        text.alignmentMode = CATextLayerAlignmentMode.center.rawValue
        text.firstMaterial?.diffuse.contents = NSColor.white
        let label = SCNNode(geometry: text)
        label.name = root.name
        let (min, max) = label.boundingBox
        label.pivot = SCNMatrix4MakeTranslation((max.x + min.x) / 2, min.y, 0)
        label.position = SCNVector3(0, 0.9, 0)
        label.constraints = [SCNBillboardConstraint()]
        root.addChildNode(label)
        return root
    }

    @MainActor
    private static func addCenter(to scene: SCNScene, integrity: Double) {
        let sphere = SCNSphere(radius: 0.75)
        sphere.segmentCount = 64
        let material = SCNMaterial()
        material.diffuse.contents = NSColor(calibratedWhite: 0.9, alpha: 1)
        material.emission.contents = NSColor(calibratedWhite: 0.9, alpha: CGFloat(max(0.2, integrity)))
        material.metalness.contents = 0.55
        material.roughness.contents = 0.18
        sphere.materials = [material]
        let node = SCNNode(geometry: sphere)
        node.name = "edge-center"
        scene.rootNode.addChildNode(node)
    }

    @MainActor
    private static func addCameraAndLights(to scene: SCNScene) {
        let camera = SCNNode()
        camera.name = "camera"
        camera.camera = SCNCamera()
        camera.camera?.fieldOfView = 48
        camera.position = SCNVector3(0, 8.2, 13.5)
        camera.look(at: SCNVector3Zero)
        scene.rootNode.addChildNode(camera)

        let key = SCNNode()
        key.light = SCNLight()
        key.light?.type = .directional
        key.light?.intensity = 1_200
        key.eulerAngles = SCNVector3(-0.9, -0.5, 0)
        scene.rootNode.addChildNode(key)

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light?.type = .ambient
        ambient.light?.color = NSColor(calibratedRed: 0.4, green: 0.48, blue: 0.55, alpha: 1)
        ambient.light?.intensity = 500
        scene.rootNode.addChildNode(ambient)
    }
}
