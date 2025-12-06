
import Foundation
import Metal
import MetalKit

enum Bagua: CaseIterable { case qian, kun, zhen, xun, kan, li, gen, dui }

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

class World {
    let width: Int
    let height: Int
    var grid: [Cell]
    let noise = PerlinNoise(seed: UInt32.random(in: 0...1000))

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
                let baguaNoise = noise.noise(x: Double(x)/40.0, y: Double(y)/40.0, z: 0)
                let baguaIndex = Int(abs(baguaNoise) * Double(Bagua.allCases.count)) % Bagua.allCases.count
                let bagua = Bagua.allCases[baguaIndex]
                
                var initialHeight = Float(noise.noise(x: Double(x)/25.0, y: Double(y)/25.0, z: 10)) * 3.5
                switch bagua {
                case .gen, .qian: initialHeight += 1.0
                case .kun, .kan: initialHeight -= 1.0
                default: break
                }
                
                let moisture = Float(noise.noise(x: Double(x)/35.0, y: Double(y)/35.0, z: 20))
                grid.append(Cell(bagua: bagua, height: initialHeight, moisture: moisture))
            }
        }
    }

    func update(deltaTime: Float) {
        for i in 0..<grid.count {
            let x = i % width
            let y = i / width
            grid[i].moisture += Float(noise.noise(x: Double(x)/15.0, y: Double(y)/15.0, z: Double(deltaTime)) * 0.05)
            grid[i].moisture = max(0, min(1, grid[i].moisture))
        }
    }
}

class Renderer: NSObject, MTKViewDelegate {

    public let device: MTLDevice
    let commandQueue: MTLCommandQueue
    var pipelineState: MTLRenderPipelineState
    var depthState: MTLDepthStencilState
    
    var world: World
    var terrainMesh: Mesh?

    var uniformBuffer: MTLBuffer

    var projectionMatrix = matrix_float4x4()
    var rotation: Float = 0.0
    var time: Float = 0.0

    enum RendererError: Error { case general(String) }

    @MainActor
    init?(metalKitView: MTKView) {
        guard let device = metalKitView.device, let commandQueue = device.makeCommandQueue() else { return nil }
        self.device = device
        self.commandQueue = commandQueue
        self.world = World(width: 150, height: 150)
        
        let uniformBufferSize = MemoryLayout<Uniforms>.stride
        guard let uniformBuffer = device.makeBuffer(length: uniformBufferSize, options: .storageModeShared) else { fatalError("Could not create uniform buffer") }
        self.uniformBuffer = uniformBuffer

        metalKitView.depthStencilPixelFormat = .depth32Float
        metalKitView.colorPixelFormat = .bgra8Unorm_srgb

        let depthDescriptor = MTLDepthStencilDescriptor()
        depthDescriptor.depthCompareFunction = .less
        depthDescriptor.isDepthWriteEnabled = true
        guard let depthState = device.makeDepthStencilState(descriptor: depthDescriptor) else { fatalError("Could not create depth state") }
        self.depthState = depthState

        do {
            pipelineState = try Renderer.buildRenderPipeline(with: device, metalKitView: metalKitView)
        } catch {
            print("Failed during pipeline initialization: \(error)")
            return nil
        }
        
        super.init()
    }
    
    @MainActor
    class func buildRenderPipeline(with device: MTLDevice, metalKitView: MTKView) throws -> MTLRenderPipelineState {
        let library = try device.makeDefaultLibrary(bundle: .main)
        guard let vertexFunction = library.makeFunction(name: "vertexShader"),
              let fragmentFunction = library.makeFunction(name: "fragmentShader") else {
            throw RendererError.general("Shader function not found")
        }

        let vertexDescriptor = MTLVertexDescriptor()
        vertexDescriptor.attributes[0].format = .float3; vertexDescriptor.attributes[0].offset = 0; vertexDescriptor.attributes[0].bufferIndex = Int(VertexBufferIndexVertices)
        vertexDescriptor.attributes[1].format = .float3; vertexDescriptor.attributes[1].offset = MemoryLayout<SIMD3<Float>>.stride; vertexDescriptor.attributes[1].bufferIndex = Int(VertexBufferIndexVertices)
        vertexDescriptor.attributes[2].format = .float4; vertexDescriptor.attributes[2].offset = MemoryLayout<SIMD3<Float>>.stride * 2; vertexDescriptor.attributes[2].bufferIndex = Int(VertexBufferIndexVertices)
        vertexDescriptor.layouts[Int(VertexBufferIndexVertices)].stride = MemoryLayout<Vertex>.stride

        let pipelineDescriptor = MTLRenderPipelineDescriptor()
        pipelineDescriptor.vertexFunction = vertexFunction
        pipelineDescriptor.fragmentFunction = fragmentFunction
        pipelineDescriptor.vertexDescriptor = vertexDescriptor
        pipelineDescriptor.colorAttachments[0].pixelFormat = metalKitView.colorPixelFormat
        pipelineDescriptor.depthAttachmentPixelFormat = metalKitView.depthStencilPixelFormat
        
        return try device.makeRenderPipelineState(descriptor: pipelineDescriptor)
    }

    private func buildTerrainMesh() throws {
        let width = world.width
        let height = world.height
        var vertices: [Vertex] = Array(repeating: Vertex(position: [0,0,0], normal: [0,1,0], color: [0,0,0,1]), count: width * height)
        let scale: Float = 15.0

        for y in 0..<height { for x in 0..<width { let index = y*width+x; let cell=world.grid[index]; let pos=SIMD3<Float>((Float(x)-Float(width)/2)/scale,cell.height/scale,(Float(y)-Float(height)/2)/scale); var color:SIMD4<Float>; switch cell.bagua{case .li:color=[1,0.2,0.2,1];case .kan:color=[0.2,0.3,1,1];case .gen:color=[0.6,0.4,0.2,1];case .xun:color=[0.1,0.8,0.1,1];default:color=[0.7,0.7,0.7,1]}; let brightness=cell.moisture*1.2+0.3; vertices[index]=Vertex(position:pos,normal:[0,1,0],color:color*brightness)}} 
        for y in 0..<height { for x in 0..<width { let index=y*width+x; let xm1=(x-1+width)%width,xp1=(x+1)%width,ym1=(y-1+height)%height,yp1=(y+1)%height; let pxm=vertices[y*width+xm1].position,pxp=vertices[y*width+xp1].position,pym=vertices[ym1*width+x].position,pyp=vertices[yp1*width+x].position; let tangent=pxp-pxm,bitangent=pyp-pym; vertices[index].normal=normalize(cross(bitangent,tangent))}}

        let quadCount = (width - 1) * (height - 1)
        let indexCount = quadCount * 6
        var indices: [UInt16] = Array(repeating: 0, count: indexCount)
        var i = 0
        for y in 0..<(height - 1) { for x in 0..<(width - 1) { let a=UInt16(y*width+x),b=a+1,c=a+UInt16(width),d=c+1; indices[i]=a;i+=1;indices[i]=b;i+=1;indices[i]=c;i+=1;indices[i]=c;i+=1;indices[i]=b;i+=1;indices[i]=d;i+=1}}

        guard let vertexBuffer = device.makeBuffer(bytes: vertices, length: vertices.count * MemoryLayout<Vertex>.stride, options: .storageModeShared), let indexBuffer = device.makeBuffer(bytes: indices, length: indices.count * MemoryLayout<UInt16>.size, options: .storageModeShared) else { throw RendererError.general("Failed to create terrain mesh buffers") }
        self.terrainMesh = Mesh(vertexBuffer: vertexBuffer, indexBuffer: indexBuffer, indexCount: indexCount)
    }
    
    private func updateUniforms(view: MTKView) {
        time += 0.01
        rotation += 0.002
        let viewMatrix = matrix4x4_translation(0, -5, -30) * matrix4x4_rotation(radians: 0.4, axis: [1,0,0]) * matrix4x4_rotation(radians: rotation, axis: [0, 1, 0])
        let uniformsPtr = uniformBuffer.contents().bindMemory(to: Uniforms.self, capacity: 1)
        uniformsPtr.pointee.projectionMatrix = projectionMatrix
        uniformsPtr.pointee.viewMatrix = viewMatrix
        uniformsPtr.pointee.lightDirection = normalize([sin(time*0.3), -0.8, cos(time*0.3)])
        uniformsPtr.pointee.modelMatrix = matrix_identity_float4x4
    }

    func draw(in view: MTKView) {
        world.update(deltaTime: time)
        if terrainMesh == nil {
            do { try buildTerrainMesh() } catch { print("Error building terrain mesh: \(error)"); return }
        }
        updateUniforms(view: view)

        guard let commandBuffer = commandQueue.makeCommandBuffer(), let renderPassDescriptor = view.currentRenderPassDescriptor, let renderEncoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor) else { return }

        renderEncoder.setRenderPipelineState(pipelineState)
        renderEncoder.setDepthStencilState(depthState)
        
        guard let mesh = terrainMesh else { return }

        renderEncoder.setVertexBuffer(mesh.vertexBuffer, offset: 0, index: Int(VertexBufferIndexVertices))
        renderEncoder.setVertexBuffer(uniformBuffer, offset: 0, index: Int(VertexBufferIndexUniforms))
        renderEncoder.drawIndexedPrimitives(type: .triangle, indexCount: mesh.indexCount, indexType: .uint16, indexBuffer: mesh.indexBuffer, indexBufferOffset: 0)

        renderEncoder.endEncoding()
        if let drawable = view.currentDrawable { commandBuffer.present(drawable) }
        commandBuffer.commit()
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {
        let aspect = Float(size.width) / Float(size.height)
        projectionMatrix = matrix_perspective_right_hand(fovyRadians: .pi / 3, aspectRatio: aspect, nearZ: 0.1, farZ: 100.0)
    }
}

class PerlinNoise { private var p: [Int] = Array(0...255); init(seed: UInt32) { var g = SystemRandomNumberGenerator(); p.shuffle(using: &g); p += p }; func noise(x: Double, y: Double, z: Double) -> Double { let X = Int(floor(x))&255, Y = Int(floor(y))&255, Z = Int(floor(z))&255; let x = x-floor(x), y = y-floor(y), z = z-floor(z); let u=fade(x),v=fade(y),w=fade(z); let A=p[X]+Y,AA=p[A]+Z,AB=p[A+1]+Z,B=p[X+1]+Y,BA=p[B]+Z,BB=p[B+1]+Z; return lerp(w,lerp(v,lerp(u,grad(p[AA],x,y,z),grad(p[BA],x-1,y,z)),lerp(u,grad(p[AB],x,y-1,z),grad(p[BB],x-1,y-1,z))),lerp(v,lerp(u,grad(p[AA+1],x,y,z-1),grad(p[BA+1],x-1,y,z-1)),lerp(u,grad(p[AB+1],x,y-1,z-1),grad(p[BB+1],x-1,y-1,z-1)))) }; private func fade(_ t: Double)->Double{t*t*t*(t*(t*6-15)+10)}; private func lerp(_ t:Double,_ a:Double,_ b:Double)->Double{a+t*(b-a)}; private func grad(_ hash:Int,_ x:Double,_ y:Double,_ z:Double)->Double{ let h=hash&15,u=h<8 ? x:y,v=h<4 ? y:h==12||h==14 ? x:z; return((h&1)==0 ? u:-u)+((h&2)==0 ? v:-v)} }
let matrix_identity_float4x4 = matrix_float4x4(1.0)
func matrix_perspective_right_hand(fovyRadians fovy: Float, aspectRatio: Float, nearZ: Float, farZ: Float) -> matrix_float4x4 { let ys=1/tanf(fovy*0.5),xs=ys/aspectRatio,zs=farZ/(nearZ-farZ); return matrix_float4x4(columns:(vector_float4(xs,0,0,0),vector_float4(0,ys,0,0),vector_float4(0,0,zs,-1),vector_float4(0,0,zs*nearZ,0))) }
func matrix4x4_rotation(radians:Float,axis:SIMD3<Float>)->matrix_float4x4{ let unitAxis=normalize(axis),ct=cosf(radians),st=sinf(radians),ci=1-ct,x=unitAxis.x,y=unitAxis.y,z=unitAxis.z; return matrix_float4x4(columns:(vector_float4(ct+x*x*ci,y*x*ci+z*st,z*x*ci-y*st,0),vector_float4(x*y*ci-z*st,ct+y*y*ci,z*y*ci+x*st,0),vector_float4(x*z*ci+y*st,y*z*ci-x*st,ct+z*z*ci,0),vector_float4(0,0,0,1))) }
func matrix4x4_translation(_ x:Float,_ y:Float,_ z:Float)->matrix_float4x4{matrix_float4x4(columns:(vector_float4(1,0,0,0),vector_float4(0,1,0,0),vector_float4(0,0,1,0),vector_float4(x,y,z,1)))}
