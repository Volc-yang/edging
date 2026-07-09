// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "EdgeWorldPreview3D",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .executable(name: "EdgeWorldPreview3D", targets: ["EdgeWorldPreview3D"]),
    ],
    targets: [
        .executableTarget(
            name: "EdgeWorldPreview3D",
            path: "Sources/EdgeWorldPreview3D"
        )
    ]
)
