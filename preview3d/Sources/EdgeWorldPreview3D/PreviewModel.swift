import Foundation

struct FourPhase4DFile: Codable {
    let seed: Int64
    let subject: String
    let dimension: String
    let count: Int
    let items: [FourPhase4DItem]
    let frameIndex: Int?
    let fps: Int?
    let layout: String?
}

struct FourPhase4DItem: Codable, Identifiable {
    let index: Int
    let coord: [Int]
    let primaryValue: Int
    let primaryName: String
    let changedValue: Int
    let changedName: String
    let changingPositions: [Int]
    let lineValuesBottomToTop: [Int]

    var id: Int { index }

    var x: Int { coord.count > 0 ? coord[0] : 0 }
    var y: Int { coord.count > 1 ? coord[1] : 0 }
    var z: Int { coord.count > 2 ? coord[2] : 0 }
    var timeStep: Int { coord.count > 3 ? coord[3] : 0 }

    var spatialCoordText: String {
        "[\(x), \(y), \(z)]"
    }

    var changeCount: Int { changingPositions.count }
}

enum PreviewColorMode: String, CaseIterable, Identifiable {
    case primary = "Primary"
    case changed = "Changed"
    case blended = "Blended"

    var id: String { rawValue }
}
