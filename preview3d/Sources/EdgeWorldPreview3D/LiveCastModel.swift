import Foundation

enum LiveCastLayout: String, CaseIterable, Identifiable, Codable {
    case oneD = "1d"
    case twoD = "2d"
    case threeD = "3d"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .oneD:
            return "1D"
        case .twoD:
            return "2D"
        case .threeD:
            return "3D"
        }
    }
}

extension FourPhase4DFile {
    var liveLayout: LiveCastLayout? {
        let key = (layout ?? dimension).lowercased()
        return LiveCastLayout(rawValue: key)
    }

    var isLiveLayout: Bool {
        liveLayout != nil
    }
}
