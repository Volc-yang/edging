
import Foundation
import Metal
import MetalKit

// MARK: - Core Philosophical Enums

enum Bagua: CaseIterable {
    case qian, kun, zhen, xun, kan, li, gen, dui
}

enum Sixiang: CaseIterable {
    case lesserYang, greaterYang, lesserYin, greaterYin
}

enum LifeCycleState: CaseIterable {
    case seed, birth, flourishing, decline, extinction
}

// MARK: - Simulation Data Structures

struct Cell {
    let bagua: Bagua
    var yin_qi: Float
    var yang_qi: Float
    var lifeCycleState: LifeCycleState
    var timeInCurrentState: Float = 0.0
}

// MARK: - World Simulation Engine

class WorldSimulation {
    let width: Int
    let height: Int
    var grid: [Cell]

    private var globalTime: Float = 0.0
    var currentSixiang: Sixiang = .lesserYang
    let seasonDuration: Float = 10.0

    let totalEnergy: Float = 1.0

    let stateDurations: [LifeCycleState: Float] = [
        .birth: 0.2, .flourishing: 1.5, .decline: 0.5
    ]

    init(width: Int, height: Int) {
        self.width = width
        self.height = height
        self.grid = []
        self.initializeGrid()
    }

    private func initializeGrid() {
        let cellCount = width * height
        grid.reserveCapacity(cellCount)
        let energyPerCell = totalEnergy / Float(cellCount)
        let noise = PerlinNoise(seed: UInt32.random(in: 0...1000))

        for y in 0..<height {
            for x in 0..<width {
                let baguaNoiseValue = noise.noise(x: Double(x) / 50.0, y: Double(y) / 50.0, z: 0)
                let baguaIndex = Int(abs(baguaNoiseValue) * Double(Bagua.allCases.count)) % Bagua.allCases.count
                let bagua = Bagua.allCases[baguaIndex]
                let initialYang = Float.random(in: 0...energyPerCell)
                let initialYin = energyPerCell - initialYang
                let cell = Cell(bagua: bagua, yin_qi: initialYin, yang_qi: initialYang, lifeCycleState: .seed)
                grid.append(cell)
            }
        }
    }

    func update(deltaTime: Float) {
        globalTime += deltaTime
        let seasonPhase = fmod(globalTime, seasonDuration * 4) / seasonDuration
        if seasonPhase < 1.0 { currentSixiang = .lesserYang }
        else if seasonPhase < 2.0 { currentSixiang = .greaterYang }
        else if seasonPhase < 3.0 { currentSixiang = .lesserYin }
        else { currentSixiang = .greaterYin }

        var nextGrid = self.grid

        for y in 0..<height {
            for x in 0..<width {
                let index = y * width + x
                var currentCell = grid[index]
                currentCell.timeInCurrentState += deltaTime

                var birthThreshold: Float = 0.45
                var declineThreshold: Float = 0.15

                switch currentCell.bagua {
                case .li: birthThreshold -= 0.1
                case .kan: birthThreshold += 0.1
                case .gen: declineThreshold *= 0.8
                default: break
                }

                switch currentSixiang {
                case .greaterYang: birthThreshold -= 0.05
                case .greaterYin: birthThreshold += 0.1
                default: break
                }

                let total_qi = currentCell.yin_qi + currentCell.yang_qi
                let ratio = total_qi > 0 ? (currentCell.yang_qi / total_qi) : 0.5
                var nextState = currentCell.lifeCycleState

                // --- SAFE State Transition Logic ---
                switch currentCell.lifeCycleState {
                case .seed:
                    if ratio > birthThreshold && ratio < (1.0 - birthThreshold) { nextState = .birth }
                case .birth:
                    if currentCell.timeInCurrentState > stateDurations[.birth]! { nextState = .flourishing }
                case .flourishing:
                    if ratio < declineThreshold || ratio > (1.0 - declineThreshold) || currentCell.timeInCurrentState > stateDurations[.flourishing]! {
                        nextState = .decline
                    }
                case .decline:
                    if currentCell.timeInCurrentState > stateDurations[.decline]! { nextState = .extinction }
                case .extinction:
                    break // Stays in extinction until reset after energy redistribution
                }

                if nextState != currentCell.lifeCycleState {
                    currentCell.lifeCycleState = nextState
                    currentCell.timeInCurrentState = 0.0
                }
                nextGrid[index] = currentCell
            }
        }
        
        for y in 0..<height {
            for x in 0..<width {
                let index = y * width + x
                if grid[index].lifeCycleState == .extinction {
                    let extinctCell = grid[index]
                    let total_qi = extinctCell.yin_qi + extinctCell.yang_qi
                    let ratio = total_qi > 0 ? (extinctCell.yang_qi / total_qi) : 0.5
                    let energyToDistribute = total_qi / 8.0

                    for dy in -1...1 {
                        for dx in -1...1 {
                            if dx == 0 && dy == 0 { continue }
                            let nx = (x + dx + width) % width
                            let ny = (y + dy + height) % height
                            let neighborIndex = ny * width + nx
                            nextGrid[neighborIndex].yin_qi += energyToDistribute * (1.0 - ratio)
                            nextGrid[neighborIndex].yang_qi += energyToDistribute * ratio
                        }
                    }
                    
                    let energyPerCell = totalEnergy / Float(width * height)
                    nextGrid[index].yin_qi = Float.random(in: 0...energyPerCell)
                    nextGrid[index].yang_qi = energyPerCell - nextGrid[index].yin_qi
                    nextGrid[index].lifeCycleState = .seed
                }
            }
        }

        grid = nextGrid
    }
}

// MARK: - Renderer

class Renderer: NSObject, MTKViewDelegate {

    public let device: MTLDevice
    let commandQueue: MTLCommandQueue
    var pipelineState: MTLRenderPipelineState
    var world: WorldSimulation
    var vertexBuffer: MTLBuffer?
    var viewportSize: vector_uint2 = .zero

    let simulationWidth = 200
    let simulationHeight = 200

    enum RendererError: Error {
        case shaderFunctionNotFound
        case pipelineCreationFailed
    }

    @MainActor
    init?(metalKitView: MTKView) {
        guard let device = metalKitView.device else { return nil }
        self.device = device
        guard let commandQueue = device.makeCommandQueue() else { return nil }
        self.commandQueue = commandQueue
        
        self.world = WorldSimulation(width: simulationWidth, height: simulationHeight)
        metalKitView.colorPixelFormat = .bgra8Unorm_srgb

        do {
            pipelineState = try Renderer.buildRenderPipeline(with: device, metalKitView: metalKitView)
        } catch {
            print("Unable to compile render pipeline state. Error: \(error)")
            return nil
        }

        super.init()
    }

    @MainActor
    class func buildRenderPipeline(with device: MTLDevice, metalKitView: MTKView) throws -> MTLRenderPipelineState {
        guard let library = device.makeDefaultLibrary() else {
            throw RendererError.shaderFunctionNotFound
        }

        guard let vertexFunction = library.makeFunction(name: "gridVertexShader") else {
            throw RendererError.shaderFunctionNotFound
        }

        guard let fragmentFunction = library.makeFunction(name: "gridFragmentShader") else {
            throw RendererError.shaderFunctionNotFound
        }

        let pipelineDescriptor = MTLRenderPipelineDescriptor()
        pipelineDescriptor.label = "GridRenderPipeline"
        pipelineDescriptor.vertexFunction = vertexFunction
        pipelineDescriptor.fragmentFunction = fragmentFunction
        pipelineDescriptor.colorAttachments[0].pixelFormat = metalKitView.colorPixelFormat
        
        do {
            return try device.makeRenderPipelineState(descriptor: pipelineDescriptor)
        } catch {
            throw RendererError.pipelineCreationFailed
        }
    }

    private func buildVertexBuffer() {
        let cellCount = world.width * world.height
        let vertexCount = cellCount * 6
        let bufferSize = vertexCount * MemoryLayout<GridVertex>.stride

        if vertexBuffer == nil || vertexBuffer!.length < bufferSize {
            guard let newBuffer = device.makeBuffer(length: bufferSize, options: .storageModeShared) else {
                print("Failed to create vertex buffer")
                return
            }
            vertexBuffer = newBuffer
            vertexBuffer?.label = "GridVertexBuffer"
        }

        guard let vertices = vertexBuffer?.contents().bindMemory(to: GridVertex.self, capacity: vertexCount) else {
            return
        }

        let cellWidth = 2.0 / Float(world.width)
        let cellHeight = 2.0 / Float(world.height)

        for y in 0..<world.height {
            for x in 0..<world.width {
                let cellIndex = y * world.width + x
                let cell = world.grid[cellIndex]

                var baseColor: vector_float4
                switch cell.bagua {
                case .li:   baseColor = vector_float4(1.0, 0.1, 0.1, 1)
                case .kan:  baseColor = vector_float4(0.1, 0.2, 1.0, 1)
                case .gen:  baseColor = vector_float4(0.6, 0.4, 0.2, 1)
                case .kun:  baseColor = vector_float4(0.5, 0.3, 0.0, 1)
                case .qian: baseColor = vector_float4(0.8, 0.8, 1.0, 1)
                case .dui:  baseColor = vector_float4(0.9, 0.9, 0.9, 1)
                case .xun:  baseColor = vector_float4(0.1, 1.0, 0.1, 1)
                case .zhen: baseColor = vector_float4(1.0, 1.0, 0.1, 1)
                }

                var stateBlendedColor: vector_float4
                if cell.lifeCycleState != .seed {
                    var stateColor: vector_float4
                    switch cell.lifeCycleState {
                    case .birth:       stateColor = vector_float4(0, 1, 0, 1)
                    case .flourishing: stateColor = vector_float4(1, 0, 0, 1)
                    case .decline:     stateColor = vector_float4(1, 1, 0, 1)
                    case .extinction:  stateColor = vector_float4(0, 0, 1, 1)
                    default: stateColor = baseColor
                    }
                    stateBlendedColor = mix(baseColor, stateColor, t: 0.5)
                } else {
                    stateBlendedColor = baseColor
                }

                let total_qi = cell.yin_qi + cell.yang_qi
                let brightness = total_qi > 0.0001 ? (cell.yang_qi / total_qi) : 0.5
                var finalColor = stateBlendedColor * (brightness * 1.2 + 0.2)
                finalColor.w = 1.0

                let startX = -1.0 + Float(x) * cellWidth
                let startY = -1.0 + Float(y) * cellHeight

                let verticesOffset = cellIndex * 6
                vertices[verticesOffset]     = GridVertex(position: [startX, startY], color: finalColor)
                vertices[verticesOffset + 1] = GridVertex(position: [startX + cellWidth, startY], color: finalColor)
                vertices[verticesOffset + 2] = GridVertex(position: [startX, startY + cellHeight], color: finalColor)
                vertices[verticesOffset + 3] = GridVertex(position: [startX, startY + cellHeight], color: finalColor)
                vertices[verticesOffset + 4] = GridVertex(position: [startX + cellWidth, startY], color: finalColor)
                vertices[verticesOffset + 5] = GridVertex(position: [startX + cellWidth, startY + cellHeight], color: finalColor)
            }
        }
    }

    func draw(in view: MTKView) {
        let deltaTime: Float = 1.0 / 60.0
        world.update(deltaTime: deltaTime)
        buildVertexBuffer()

        guard let commandBuffer = commandQueue.makeCommandBuffer(),
              let renderPassDescriptor = view.currentRenderPassDescriptor,
              let renderEncoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor) else { return }

        renderEncoder.setViewport(MTLViewport(originX: 0.0, originY: 0.0, width: Double(viewportSize.x), height: Double(viewportSize.y), znear: 0.0, zfar: 1.0))
        renderEncoder.setRenderPipelineState(pipelineState)
        renderEncoder.setVertexBuffer(vertexBuffer, offset: 0, index: 0)
        renderEncoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: world.width * world.height * 6)
        renderEncoder.endEncoding()

        if let drawable = view.currentDrawable {
            commandBuffer.present(drawable)
        }
        commandBuffer.commit()
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {
        viewportSize.x = UInt32(size.width)
        viewportSize.y = UInt32(size.height)
    }
}

// MARK: - Perlin Noise Generator

fileprivate class PerlinNoise {
    private var p: [Int] = Array(0...255)

    init(seed: UInt32) {
        var generator = SystemRandomNumberGenerator()
        p.shuffle(using: &generator)
        p += p // Duplicate to avoid overflow
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

        return lerp(w, lerp(v, lerp(u, grad(p[AA], x, y, z), grad(p[BA], x - 1, y, z)),
                               lerp(u, grad(p[AB], x, y - 1, z), grad(p[BB], x - 1, y - 1, z))),
                       lerp(v, lerp(u, grad(p[AA + 1], x, y, z - 1), grad(p[BA + 1], x - 1, y, z - 1)),
                               lerp(u, grad(p[AB + 1], x, y - 1, z - 1), grad(p[BB + 1], x - 1, y - 1, z - 1))))
    }

    private func fade(_ t: Double) -> Double { t * t * t * (t * (t * 6 - 15) + 10) }
    private func lerp(_ t: Double, _ a: Double, _ b: Double) -> Double { a + t * (b - a) }
    private func grad(_ hash: Int, _ x: Double, _ y: Double, _ z: Double) -> Double {
        let h = hash & 15
        let u = h < 8 ? x : y
        let v = h < 4 ? y : h == 12 || h == 14 ? x : z
        return ((h & 1) == 0 ? u : -u) + ((h & 2) == 0 ? v : -v)
    }
}
