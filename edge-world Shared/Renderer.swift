import Foundation
import Metal
import MetalKit
import simd

enum Bagua: CaseIterable {
    case qian
    case kun
    case zhen
    case xun
    case kan
    case li
    case gen
    case dui
}

struct Cell {
    let bagua: Bagua
    var height: Float
    var moisture: Float
}

struct Mesh {
    let vertexBuffer: MTLBuffer
    let indexBuffer: MTLBuffer
    let indexCount: Int
}

struct HexagramVolumeMesh {
    let mesh: Mesh
    let title: String
}

struct HexagramVolumeDefinition {
    let title: String
    let origin: SIMD3<Float>
    let values: [[[Int]]]
}

final class World {
    let width: Int
    let height: Int
    var grid: [Cell]
    let noise = PerlinNoise(seed: 20260627)

    init(width: Int, height: Int) {
        self.width = width
        self.height = height
        self.grid = []
        initializeGrid()
    }

    private func initializeGrid() {
        grid.reserveCapacity(width * height)
        for y in 0..<height {
            for x in 0..<width {
                let baguaNoise = noise.noise(x: Double(x) / 40.0, y: Double(y) / 40.0, z: 0.0)
                let baguaIndex = Int(abs(baguaNoise) * Double(Bagua.allCases.count)) % Bagua.allCases.count
                let bagua = Bagua.allCases[baguaIndex]

                var initialHeight = Float(noise.noise(x: Double(x) / 25.0, y: Double(y) / 25.0, z: 10.0)) * 3.5
                switch bagua {
                case .gen, .qian:
                    initialHeight += 1.0
                case .kun, .kan:
                    initialHeight -= 1.0
                default:
                    break
                }

                let moisture = Float(noise.noise(x: Double(x) / 35.0, y: Double(y) / 35.0, z: 20.0))
                grid.append(Cell(bagua: bagua, height: initialHeight, moisture: moisture))
            }
        }
    }

    func update(deltaTime: Float) {
        for index in grid.indices {
            let x = index % width
            let y = index / width
            grid[index].moisture += Float(
                noise.noise(x: Double(x) / 15.0, y: Double(y) / 15.0, z: Double(deltaTime)) * 0.05
            )
            grid[index].moisture = max(0.0, min(1.0, grid[index].moisture))
        }
    }
}

final class Renderer: NSObject, MTKViewDelegate {
    let device: MTLDevice
    let commandQueue: MTLCommandQueue
    let pipelineState: MTLRenderPipelineState
    let depthState: MTLDepthStencilState

    var world: World
    var terrainMesh: Mesh?
    var hexagramVolumeMeshes: [HexagramVolumeMesh] = []

    let uniformBuffer: MTLBuffer
    let emptyGodBuffer: MTLBuffer

    var projectionMatrix = matrix_identity_float4x4
    var rotation: Float = 0.0
    var time: Float = 0.0
    private var hasLoggedFirstDraw = false

    enum RendererError: Error {
        case general(String)
    }

    @MainActor
    init?(metalKitView: MTKView) {
        guard
            let device = metalKitView.device,
            let commandQueue = device.makeCommandQueue()
        else {
            return nil
        }

        self.device = device
        self.commandQueue = commandQueue
        self.world = World(width: 150, height: 150)

        let uniformBufferSize = MemoryLayout<Uniforms>.stride
        guard let uniformBuffer = device.makeBuffer(length: uniformBufferSize, options: .storageModeShared) else {
            fatalError("Could not create uniform buffer")
        }
        self.uniformBuffer = uniformBuffer
        guard let emptyGodBuffer = device.makeBuffer(length: max(MemoryLayout<GodProjection>.stride, 16), options: .storageModeShared) else {
            fatalError("Could not create fallback god buffer")
        }
        self.emptyGodBuffer = emptyGodBuffer

        metalKitView.depthStencilPixelFormat = .depth32Float
        metalKitView.colorPixelFormat = .bgra8Unorm_srgb
        metalKitView.clearColor = MTLClearColor(red: 0.06, green: 0.07, blue: 0.09, alpha: 1.0)

        let depthDescriptor = MTLDepthStencilDescriptor()
        depthDescriptor.depthCompareFunction = .less
        depthDescriptor.isDepthWriteEnabled = true
        guard let depthState = device.makeDepthStencilState(descriptor: depthDescriptor) else {
            fatalError("Could not create depth state")
        }
        self.depthState = depthState

        do {
            pipelineState = try Renderer.buildRenderPipeline(with: device, metalKitView: metalKitView)
        } catch {
            print("Failed during pipeline initialization: \(error)")
            return nil
        }

        super.init()
        initializeSceneMeshes()
    }

    @MainActor
    class func buildRenderPipeline(with device: MTLDevice, metalKitView: MTKView) throws -> MTLRenderPipelineState {
        let library = try loadShaderLibrary(with: device)
        guard
            let vertexFunction = library.makeFunction(name: "vertexShader"),
            let fragmentFunction = library.makeFunction(name: "fragmentShader")
        else {
            throw RendererError.general("Shader function not found")
        }

        let vertexDescriptor = MTLVertexDescriptor()
        vertexDescriptor.attributes[0].format = .float3
        vertexDescriptor.attributes[0].offset = 0
        vertexDescriptor.attributes[0].bufferIndex = Int(VertexBufferIndexVertices)
        vertexDescriptor.attributes[1].format = .float3
        vertexDescriptor.attributes[1].offset = MemoryLayout<SIMD3<Float>>.stride
        vertexDescriptor.attributes[1].bufferIndex = Int(VertexBufferIndexVertices)
        vertexDescriptor.attributes[2].format = .float4
        vertexDescriptor.attributes[2].offset = MemoryLayout<SIMD3<Float>>.stride * 2
        vertexDescriptor.attributes[2].bufferIndex = Int(VertexBufferIndexVertices)
        vertexDescriptor.layouts[Int(VertexBufferIndexVertices)].stride = MemoryLayout<Vertex>.stride

        let pipelineDescriptor = MTLRenderPipelineDescriptor()
        pipelineDescriptor.vertexFunction = vertexFunction
        pipelineDescriptor.fragmentFunction = fragmentFunction
        pipelineDescriptor.vertexDescriptor = vertexDescriptor
        pipelineDescriptor.colorAttachments[0].pixelFormat = metalKitView.colorPixelFormat
        pipelineDescriptor.depthAttachmentPixelFormat = metalKitView.depthStencilPixelFormat

        return try device.makeRenderPipelineState(descriptor: pipelineDescriptor)
    }

    @MainActor
    private class func loadShaderLibrary(with device: MTLDevice) throws -> MTLLibrary {
        if
            let shaderURL = Bundle.main.url(forResource: "Shaders.metal", withExtension: "txt"),
            let shaderSource = try? String(contentsOf: shaderURL, encoding: .utf8)
        {
            let options = MTLCompileOptions()
            options.languageVersion = .version3_2
            return try device.makeLibrary(source: shaderSource, options: options)
        }

        return try device.makeDefaultLibrary(bundle: .main)
    }

    private func initializeSceneMeshes() {
        do {
            try buildTerrainMesh()
            hexagramVolumeMeshes = try Self.hexagramVolumeDefinitions.map { definition in
                try buildHexagramVolumeMesh(
                    values: definition.values,
                    title: definition.title,
                    origin: definition.origin
                )
            }
            let summaries = Self.hexagramVolumeDefinitions.map {
                "\($0.title)=\($0.values.count)x\($0.values.first?.count ?? 0)x\($0.values.first?.first?.count ?? 0)"
            }.joined(separator: ", ")
            NSLog("[EdgeWorld] Hexagram volumes initialized: \(summaries)")
        } catch {
            NSLog("Failed to initialize scene meshes: \(error.localizedDescription)")
        }
    }

    private func buildTerrainMesh() throws {
        let width = world.width
        let height = world.height
        var vertices = Array(
            repeating: Vertex(position: [0, 0, 0], normal: [0, 1, 0], color: [0, 0, 0, 1]),
            count: width * height
        )
        let scale: Float = 15.0

        for y in 0..<height {
            for x in 0..<width {
                let index = y * width + x
                let cell = world.grid[index]
                let position = SIMD3<Float>(
                    (Float(x) - Float(width) / 2.0) / scale,
                    cell.height / scale,
                    (Float(y) - Float(height) / 2.0) / scale
                )
                var color: SIMD4<Float>
                switch cell.bagua {
                case .li:
                    color = [1.0, 0.2, 0.2, 1.0]
                case .kan:
                    color = [0.2, 0.3, 1.0, 1.0]
                case .gen:
                    color = [0.6, 0.4, 0.2, 1.0]
                case .xun:
                    color = [0.1, 0.8, 0.1, 1.0]
                default:
                    color = [0.7, 0.7, 0.7, 1.0]
                }
                let brightness = cell.moisture * 1.2 + 0.3
                vertices[index] = Vertex(
                    position: position,
                    normal: [0, 1, 0],
                    color: color * brightness
                )
            }
        }

        for y in 0..<height {
            for x in 0..<width {
                let index = y * width + x
                let xm1 = (x - 1 + width) % width
                let xp1 = (x + 1) % width
                let ym1 = (y - 1 + height) % height
                let yp1 = (y + 1) % height

                let pxm = vertices[y * width + xm1].position
                let pxp = vertices[y * width + xp1].position
                let pym = vertices[ym1 * width + x].position
                let pyp = vertices[yp1 * width + x].position
                let tangent = pxp - pxm
                let bitangent = pyp - pym
                vertices[index].normal = normalize(cross(bitangent, tangent))
            }
        }

        var indices: [UInt16] = []
        indices.reserveCapacity((width - 1) * (height - 1) * 6)
        for y in 0..<(height - 1) {
            for x in 0..<(width - 1) {
                let a = UInt16(y * width + x)
                let b = a + 1
                let c = a + UInt16(width)
                let d = c + 1
                indices += [a, b, c, c, b, d]
            }
        }

        guard
            let vertexBuffer = device.makeBuffer(
                bytes: vertices,
                length: vertices.count * MemoryLayout<Vertex>.stride,
                options: .storageModeShared
            ),
            let indexBuffer = device.makeBuffer(
                bytes: indices,
                length: indices.count * MemoryLayout<UInt16>.stride,
                options: .storageModeShared
            )
        else {
            throw RendererError.general("Failed to create terrain mesh buffers")
        }

        terrainMesh = Mesh(vertexBuffer: vertexBuffer, indexBuffer: indexBuffer, indexCount: indices.count)
    }

    private func buildHexagramVolumeMesh(
        values: [[[Int]]],
        title: String,
        origin: SIMD3<Float>
    ) throws -> HexagramVolumeMesh {
        let voxelSize: Float = 0.72
        let gap: Float = 0.06
        let spacing = voxelSize + gap

        var vertices: [Vertex] = []
        var indices: [UInt16] = []
        vertices.reserveCapacity(values.count * values[0].count * values[0][0].count * 24)
        indices.reserveCapacity(values.count * values[0].count * values[0][0].count * 36)

        for z in 0..<values.count {
            for y in 0..<values[z].count {
                for x in 0..<values[z][y].count {
                    let value = values[z][y][x]
                    let color = Self.hexagramColor(for: value)
                    let center = origin + SIMD3<Float>(
                        (Float(x) - 1.5) * spacing,
                        Float(y) * spacing,
                        (Float(z) - 1.5) * spacing
                    )
                    appendCube(
                        center: center,
                        size: voxelSize,
                        color: color,
                        vertices: &vertices,
                        indices: &indices
                    )
                }
            }
        }

        guard
            let vertexBuffer = device.makeBuffer(
                bytes: vertices,
                length: vertices.count * MemoryLayout<Vertex>.stride,
                options: .storageModeShared
            ),
            let indexBuffer = device.makeBuffer(
                bytes: indices,
                length: indices.count * MemoryLayout<UInt16>.stride,
                options: .storageModeShared
            )
        else {
            throw RendererError.general("Failed to create hexagram volume buffers")
        }

        return HexagramVolumeMesh(
            mesh: Mesh(vertexBuffer: vertexBuffer, indexBuffer: indexBuffer, indexCount: indices.count),
            title: title
        )
    }

    private func appendCube(
        center: SIMD3<Float>,
        size: Float,
        color: SIMD4<Float>,
        vertices: inout [Vertex],
        indices: inout [UInt16]
    ) {
        let half = size * 0.5
        let p000 = center + SIMD3<Float>(-half, -half, -half)
        let p001 = center + SIMD3<Float>(-half, -half, half)
        let p010 = center + SIMD3<Float>(-half, half, -half)
        let p011 = center + SIMD3<Float>(-half, half, half)
        let p100 = center + SIMD3<Float>(half, -half, -half)
        let p101 = center + SIMD3<Float>(half, -half, half)
        let p110 = center + SIMD3<Float>(half, half, -half)
        let p111 = center + SIMD3<Float>(half, half, half)

        let baseIndex = UInt16(vertices.count)

        let faceColors = Self.cubeFaceColors(from: color)
        let faces: [([SIMD3<Float>], SIMD3<Float>, SIMD4<Float>)] = [
            ([p001, p101, p111, p011], [0, 0, 1], faceColors.front),
            ([p100, p000, p010, p110], [0, 0, -1], faceColors.back),
            ([p000, p001, p011, p010], [-1, 0, 0], faceColors.left),
            ([p101, p100, p110, p111], [1, 0, 0], faceColors.right),
            ([p010, p011, p111, p110], [0, 1, 0], faceColors.top),
            ([p000, p100, p101, p001], [0, -1, 0], faceColors.bottom),
        ]

        for face in faces {
            for position in face.0 {
                vertices.append(Vertex(position: position, normal: face.1, color: face.2))
            }
        }

        for faceIndex in 0..<6 {
            let faceBase = baseIndex + UInt16(faceIndex * 4)
            indices += [
                faceBase, faceBase + 1, faceBase + 2,
                faceBase, faceBase + 2, faceBase + 3,
            ]
        }
    }

    private func updateUniforms() {
        time += 0.01
        rotation += 0.002

        let viewMatrix =
            matrix4x4_translation(0.0, -3.2, -24.0) *
            matrix4x4_rotation(radians: 0.48, axis: [1, 0, 0]) *
            matrix4x4_rotation(radians: rotation, axis: [0, 1, 0])

        let uniformsPtr = uniformBuffer.contents().bindMemory(to: Uniforms.self, capacity: 1)
        uniformsPtr.pointee.projectionMatrix = projectionMatrix
        uniformsPtr.pointee.viewMatrix = viewMatrix
        uniformsPtr.pointee.modelMatrix = matrix_identity_float4x4
        uniformsPtr.pointee.lightDirection = normalize([sin(time * 0.3), -0.8, cos(time * 0.3)])
        uniformsPtr.pointee.godCount = 0
        uniformsPtr.pointee.time = time
    }

    func draw(in view: MTKView) {
        world.update(deltaTime: time)
        updateUniforms()

        guard
            let commandBuffer = commandQueue.makeCommandBuffer(),
            let renderPassDescriptor = view.currentRenderPassDescriptor,
            let renderEncoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor)
        else {
            return
        }

        renderEncoder.setRenderPipelineState(pipelineState)
        renderEncoder.setDepthStencilState(depthState)
        renderEncoder.setVertexBuffer(uniformBuffer, offset: 0, index: Int(VertexBufferIndexUniforms))
        renderEncoder.setFragmentBuffer(uniformBuffer, offset: 0, index: Int(VertexBufferIndexUniforms))
        renderEncoder.setFragmentBuffer(emptyGodBuffer, offset: 0, index: Int(VertexBufferIndexGods))

        if let terrainMesh {
            renderEncoder.setVertexBuffer(terrainMesh.vertexBuffer, offset: 0, index: Int(VertexBufferIndexVertices))
            renderEncoder.drawIndexedPrimitives(
                type: .triangle,
                indexCount: terrainMesh.indexCount,
                indexType: .uint16,
                indexBuffer: terrainMesh.indexBuffer,
                indexBufferOffset: 0
            )
        }

        for volume in hexagramVolumeMeshes {
            renderEncoder.setVertexBuffer(volume.mesh.vertexBuffer, offset: 0, index: Int(VertexBufferIndexVertices))
            renderEncoder.drawIndexedPrimitives(
                type: .triangle,
                indexCount: volume.mesh.indexCount,
                indexType: .uint16,
                indexBuffer: volume.mesh.indexBuffer,
                indexBufferOffset: 0
            )
        }

        if !hasLoggedFirstDraw {
            hasLoggedFirstDraw = true
            let meshCount = hexagramVolumeMeshes.count
            let indexCounts = hexagramVolumeMeshes.map { "\($0.title)=\($0.mesh.indexCount)" }.joined(separator: ", ")
            NSLog("[EdgeWorld] First frame drew terrain plus \(meshCount) hexagram volume meshes: \(indexCounts)")
        }

        renderEncoder.endEncoding()
        if let drawable = view.currentDrawable {
            commandBuffer.present(drawable)
        }
        commandBuffer.commit()
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {
        let aspect = max(0.1, Float(size.width) / Float(size.height))
        projectionMatrix = matrix_perspective_right_hand(
            fovyRadians: .pi / 3.0,
            aspectRatio: aspect,
            nearZ: 0.1,
            farZ: 100.0
        )
    }
}

private extension Renderer {
    struct FacePalette {
        let top: SIMD4<Float>
        let front: SIMD4<Float>
        let back: SIMD4<Float>
        let left: SIMD4<Float>
        let right: SIMD4<Float>
        let bottom: SIMD4<Float>
    }

    static let primaryVolumeValues: [[[Int]]] = [
        [[37, 49, 44, 31], [50, 51, 39, 61], [36, 21, 62, 58], [47, 53, 33, 53]],
        [[35, 57, 33, 2], [35, 61, 3, 10], [58, 47, 33, 2], [13, 27, 28, 30]],
        [[32, 33, 57, 6], [22, 30, 57, 10], [50, 52, 62, 14], [29, 54, 28, 12]],
        [[21, 14, 12, 55], [46, 13, 31, 5], [53, 7, 31, 27], [19, 2, 62, 28]],
    ]

    static let changedVolumeValues: [[[Int]]] = [
        [[4, 57, 4, 22], [16, 17, 39, 60], [32, 20, 58, 42], [36, 49, 9, 52]],
        [[0, 41, 1, 10], [3, 44, 35, 34], [58, 9, 16, 2], [2, 15, 8, 30]],
        [[32, 34, 41, 34], [4, 14, 45, 2], [22, 56, 62, 6], [29, 24, 0, 4]],
        [[4, 0, 12, 48], [56, 8, 4, 4], [48, 7, 14, 18], [11, 0, 62, 20]],
    ]

    static let hexagramVolumeDefinitions: [HexagramVolumeDefinition] = [
        HexagramVolumeDefinition(
            title: "Primary Hexagram Body",
            origin: SIMD3<Float>(-3.4, 1.8, 0.0),
            values: primaryVolumeValues
        ),
        HexagramVolumeDefinition(
            title: "Changed Hexagram Body",
            origin: SIMD3<Float>(3.4, 1.8, 0.0),
            values: changedVolumeValues
        ),
    ]

    static func hexagramColor(for value: Int) -> SIMD4<Float> {
        let hue = Float(value % 64) / 64.0
        let saturation: Float = 0.72
        let brightness: Float = 0.94
        let rgb = hsvToRgb(h: hue, s: saturation, v: brightness)
        return SIMD4<Float>(rgb.x, rgb.y, rgb.z, 1.0)
    }

    static func cubeFaceColors(from base: SIMD4<Float>) -> FacePalette {
        FacePalette(
            top: tint(base, factor: 1.05),
            front: tint(base, factor: 0.92),
            back: tint(base, factor: 0.78),
            left: tint(base, factor: 0.72),
            right: tint(base, factor: 0.84),
            bottom: tint(base, factor: 0.58)
        )
    }

    static func tint(_ color: SIMD4<Float>, factor: Float) -> SIMD4<Float> {
        SIMD4<Float>(
            min(max(color.x * factor, 0.0), 1.0),
            min(max(color.y * factor, 0.0), 1.0),
            min(max(color.z * factor, 0.0), 1.0),
            color.w
        )
    }

    static func hsvToRgb(h: Float, s: Float, v: Float) -> SIMD3<Float> {
        let wrappedHue = h - floor(h)
        let i = Int(wrappedHue * 6.0)
        let f = wrappedHue * 6.0 - Float(i)
        let p = v * (1.0 - s)
        let q = v * (1.0 - f * s)
        let t = v * (1.0 - (1.0 - f) * s)

        switch i % 6 {
        case 0:
            return SIMD3<Float>(v, t, p)
        case 1:
            return SIMD3<Float>(q, v, p)
        case 2:
            return SIMD3<Float>(p, v, t)
        case 3:
            return SIMD3<Float>(p, q, v)
        case 4:
            return SIMD3<Float>(t, p, v)
        default:
            return SIMD3<Float>(v, p, q)
        }
    }
}

final class PerlinNoise {
    private var p: [Int] = Array(0...255)

    init(seed: UInt32) {
        var generator = SeededGenerator(state: UInt64(seed))
        p.shuffle(using: &generator)
        p += p
    }

    func noise(x: Double, y: Double, z: Double) -> Double {
        let X = Int(floor(x)) & 255
        let Y = Int(floor(y)) & 255
        let Z = Int(floor(z)) & 255

        let x = x - floor(x)
        let y = y - floor(y)
        let z = z - floor(z)

        let u = fade(x)
        let v = fade(y)
        let w = fade(z)

        let A = p[X] + Y
        let AA = p[A] + Z
        let AB = p[A + 1] + Z
        let B = p[X + 1] + Y
        let BA = p[B] + Z
        let BB = p[B + 1] + Z

        return lerp(
            w,
            lerp(
                v,
                lerp(u, grad(p[AA], x, y, z), grad(p[BA], x - 1.0, y, z)),
                lerp(u, grad(p[AB], x, y - 1.0, z), grad(p[BB], x - 1.0, y - 1.0, z))
            ),
            lerp(
                v,
                lerp(u, grad(p[AA + 1], x, y, z - 1.0), grad(p[BA + 1], x - 1.0, y, z - 1.0)),
                lerp(u, grad(p[AB + 1], x, y - 1.0, z - 1.0), grad(p[BB + 1], x - 1.0, y - 1.0, z - 1.0))
            )
        )
    }

    private func fade(_ t: Double) -> Double {
        t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    }

    private func lerp(_ t: Double, _ a: Double, _ b: Double) -> Double {
        a + t * (b - a)
    }

    private func grad(_ hash: Int, _ x: Double, _ y: Double, _ z: Double) -> Double {
        let h = hash & 15
        let u = h < 8 ? x : y
        let v = h < 4 ? y : (h == 12 || h == 14 ? x : z)
        return ((h & 1) == 0 ? u : -u) + ((h & 2) == 0 ? v : -v)
    }
}

struct SeededGenerator: RandomNumberGenerator {
    var state: UInt64

    mutating func next() -> UInt64 {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        return state
    }
}

let matrix_identity_float4x4 = matrix_float4x4(1.0)

func matrix_perspective_right_hand(
    fovyRadians fovy: Float,
    aspectRatio: Float,
    nearZ: Float,
    farZ: Float
) -> matrix_float4x4 {
    let ys = 1.0 / tanf(fovy * 0.5)
    let xs = ys / aspectRatio
    let zs = farZ / (nearZ - farZ)

    return matrix_float4x4(
        columns: (
            vector_float4(xs, 0, 0, 0),
            vector_float4(0, ys, 0, 0),
            vector_float4(0, 0, zs, -1),
            vector_float4(0, 0, zs * nearZ, 0)
        )
    )
}

func matrix4x4_rotation(radians: Float, axis: SIMD3<Float>) -> matrix_float4x4 {
    let unitAxis = normalize(axis)
    let ct = cosf(radians)
    let st = sinf(radians)
    let ci = 1.0 - ct
    let x = unitAxis.x
    let y = unitAxis.y
    let z = unitAxis.z

    return matrix_float4x4(
        columns: (
            vector_float4(ct + x * x * ci, y * x * ci + z * st, z * x * ci - y * st, 0),
            vector_float4(x * y * ci - z * st, ct + y * y * ci, z * y * ci + x * st, 0),
            vector_float4(x * z * ci + y * st, y * z * ci - x * st, ct + z * z * ci, 0),
            vector_float4(0, 0, 0, 1)
        )
    )
}

func matrix4x4_translation(_ x: Float, _ y: Float, _ z: Float) -> matrix_float4x4 {
    matrix_float4x4(
        columns: (
            vector_float4(1, 0, 0, 0),
            vector_float4(0, 1, 0, 0),
            vector_float4(0, 0, 1, 0),
            vector_float4(x, y, z, 1)
        )
    )
}
