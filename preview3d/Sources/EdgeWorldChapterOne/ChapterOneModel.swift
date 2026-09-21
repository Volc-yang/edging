import Foundation

struct ChapterOneSnapshot: Decodable {
    let schemaVersion: String
    let chapter: String
    let seed: Int
    let tick: Int
    let cosmology: Cosmology
    let decision: DecisionEnvelope
    let encounter: Encounter
    let worldResponse: WorldResponse
    let presentation: EncounterPresentation
    let validation: ChapterValidation
    let cycle: PrimalCycle
    let spirits: [SpiritSnapshot]
}

struct Cosmology: Decodable {
    let worldOrder: String
    let changeOrder: String
    let changeCanon: String
    let xiantianWorld: XiantianWorld
    let playerIntervention: PlayerIntervention
    let houtianTransition: HoutianTransition
}

struct XiantianWorld: Decodable {
    let phase: Int
    let spirit: String
    let trigramName: String
    let symbol: String
    let direction: String
}

struct PlayerIntervention: Decodable {
    let actionAxis: String
    let intensity: Double
    let expression: String
}

struct HoutianTransition: Decodable {
    let focusSpirit: String
    let direction: String
    let luoshuNumber: Int
    let aiFocusSpirit: String
    let playerSpirit: String
    let playerDirection: String
    let playerLuoshuNumber: Int
}

struct Encounter: Decodable {
    let primaryHexagram: HexagramEncounter
    let changingPositions: [Int]
    let governingLine: GoverningLine
    let changedHexagram: HexagramEncounter
}

struct GoverningLine: Decodable {
    let position: Int
    let name: String
    let polarity: String
    let text: String
    let commentary: String
    let evidenceScore: Double
    let evidenceAxes: [String]
}

struct HexagramEncounter: Decodable {
    let value: Int
    let sequence: Int
    let name: String
    let symbol: String
    let upperTrigram: String
    let lowerTrigram: String
    let judgment: String
    let image: String
    let canonicalTextAvailable: Bool
    let structuralImage: String
}

struct EncounterPresentation: Decodable {
    let source: String
    let title: String
    let scene: String
    let omen: String
    let playerPrompt: String
    let fallbackReason: String?
}

struct WorldResponse: Decodable {
    let forecast: WorldForecast
    let control: WorldControl
    let feedback: WorldFeedback
}

struct WorldForecast: Decodable {
    let primaryJudgment: String
    let governingLineName: String
    let governingLineText: String
    let changedJudgment: String
    let valence: String
    let tendency: String
    let summary: String
}

struct WorldControl: Decodable {
    let targetSpirit: String
    let actionAxis: String
    let effect: String
    let effectCn: String
    let magnitude: Double
    let durationTicks: Int
    let scaleMultiplier: Double
    let emissionMultiplier: Double
    let verticalOffset: Double
}

struct WorldFeedback: Decodable {
    let status: String
    let entityId: String
    let before: SpiritSignature
    let after: SpiritSignature
    let changedHexagramValue: Int
    let message: String
}

struct DecisionEnvelope: Decodable {
    let source: String
    let model: String
    let accepted: Bool
    let fallbackReason: String?
    let decision: DevelopmentDecision
}

struct DevelopmentDecision: Decodable {
    let focusSpirit: String
    let actionIntents: [String: Double]
    let rationale: String
}

struct ChapterValidation: Decodable {
    let success: Bool
    let score: Double
}

struct PrimalCycle: Decodable {
    let initialIntegrity: Double
    let finalIntegrity: Double
    let completed: Bool
    let steps: [PrimalStep]
}

struct PrimalStep: Decodable {
    let order: Int
    let phrase: String
    let spiritId: String
    let actionAxis: String
    let nextIntegrity: Double
}

struct SpiritSnapshot: Decodable, Identifiable {
    let slug: String
    let name: String
    let trigramName: String
    let symbol: String
    let description: String
    let entity: SpiritEntity

    var id: String { slug }
}

struct SpiritEntity: Decodable {
    let status: String
    let regionId: RegionIdentifier
    let signature: SpiritSignature
}

struct RegionIdentifier: Decodable {
    let x: Int
    let y: Int
}

struct SpiritSignature: Decodable {
    let consciousness: Double
    let coherence: Double
    let entropy: Double
}
