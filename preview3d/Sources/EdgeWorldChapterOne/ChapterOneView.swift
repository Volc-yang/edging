import SwiftUI

struct ChapterOneView: View {
    @ObservedObject var store: ChapterOneStore

    var body: some View {
        HStack(spacing: 0) {
            SpiritSceneView(store: store)
                .frame(minWidth: 820, minHeight: 720)

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("EDGE WORLD")
                        .font(.system(size: 25, weight: .semibold))
                    Text("第一章 · 万物有灵")
                        .font(.system(size: 17, weight: .medium))
                    Text(store.status)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(.secondary)

                    if let snapshot = store.snapshot {
                        statusBlock(snapshot)
                        interventionBlock()
                        cosmologyBlock(snapshot)
                        encounterBlock(snapshot)
                        decisionBlock(snapshot.decision)
                        spiritBlock(store.selected)
                        cycleBlock(snapshot.cycle)
                    }

                    HStack {
                        Button("Ollama 推演") { store.run(offline: false) }
                        Button("规则回退") { store.run(offline: true) }
                    }
                    .disabled(store.isRunning)
                }
                .padding(22)
            }
            .frame(width: 390)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }

    private func interventionBlock() -> some View {
        GroupBox("玩家介入变量") {
            VStack(alignment: .leading, spacing: 9) {
                Picker("动作", selection: $store.playerAction) {
                    ForEach(ChapterOneStore.playerActions, id: \.self) { Text($0).tag($0) }
                }.pickerStyle(.menu)
                HStack {
                    Text("强度")
                    Slider(value: $store.playerIntensity, in: 0.1...1.0, step: 0.1)
                    Text(String(format: "%.1f", store.playerIntensity)).monospacedDigit()
                }
                TextField("玩家如何介入", text: $store.playerExpression)
            }
        }
    }

    private func cosmologyBlock(_ snapshot: ChapterOneSnapshot) -> some View {
        let state = snapshot.cosmology.xiantianWorld
        let transition = snapshot.cosmology.houtianTransition
        return GroupBox("先天运行 → 后天转变") {
            VStack(alignment: .leading, spacing: 7) {
                value("先天", "\(state.symbol) \(state.trigramName) / \(state.spirit) · \(state.direction)")
                value("玩家", "\(snapshot.cosmology.playerIntervention.actionAxis) · \(snapshot.cosmology.playerIntervention.intensity)")
                value("后天", "\(transition.focusSpirit) · \(transition.direction) · 洛书\(transition.luoshuNumber)")
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func encounterBlock(_ snapshot: ChapterOneSnapshot) -> some View {
        let encounter = snapshot.encounter
        let presentation = snapshot.presentation
        return GroupBox("周易遭遇") {
            VStack(alignment: .leading, spacing: 8) {
                Text("\(encounter.primaryHexagram.symbol) \(encounter.primaryHexagram.name)  →  \(encounter.changedHexagram.symbol) \(encounter.changedHexagram.name)")
                    .font(.headline)
                value("动爻", encounter.changingPositions.map(String.init).joined(separator: ", "))
                value("主导爻", "\(encounter.governingLine.name) · \(encounter.governingLine.evidenceAxes.joined(separator: ","))")
                Text("卦辞：\(encounter.primaryHexagram.judgment)").foregroundStyle(.secondary)
                Text("爻辞：\(encounter.governingLine.text)").foregroundStyle(.secondary)
                Text("预判：\(snapshot.worldResponse.forecast.tendency)").fontWeight(.medium)
                Text("反馈：\(snapshot.worldResponse.feedback.message)").foregroundStyle(.secondary)
                Text(presentation.title).fontWeight(.medium)
                Text(presentation.scene).foregroundStyle(.secondary)
                Text(presentation.omen).foregroundStyle(.secondary)
                Text(presentation.playerPrompt).fontWeight(.medium)
                if !encounter.primaryHexagram.canonicalTextAvailable {
                    Text("本卦原典文本尚未录入，当前显示结构之象。")
                        .font(.caption).foregroundStyle(.orange)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func statusBlock(_ snapshot: ChapterOneSnapshot) -> some View {
        GroupBox("规则状态") {
            VStack(alignment: .leading, spacing: 7) {
                value("验收", snapshot.validation.success ? "通过" : "失败")
                value("得分", String(format: "%.4f", snapshot.validation.score))
                value("八阶段", snapshot.cycle.completed ? "完成" : "未完成")
                value("中宫", String(format: "%.4f", snapshot.cycle.finalIntegrity))
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func decisionBlock(_ envelope: DecisionEnvelope) -> some View {
        GroupBox("本地 AI 决策") {
            VStack(alignment: .leading, spacing: 7) {
                value("来源", envelope.source)
                value("模型", envelope.model)
                value("焦点", envelope.decision.focusSpirit)
                value("意图", envelope.decision.actionIntents.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }.joined(separator: ", "))
                Text(envelope.decision.rationale).foregroundStyle(.secondary)
                if let reason = envelope.fallbackReason {
                    Text("回退原因：\(reason)").foregroundStyle(.orange)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func spiritBlock(_ spirit: SpiritSnapshot?) -> some View {
        GroupBox("灵体") {
            if let spirit {
                VStack(alignment: .leading, spacing: 7) {
                    Text("\(spirit.symbol) \(spirit.trigramName) / \(spirit.slug)").font(.headline)
                    Text(spirit.description).foregroundStyle(.secondary)
                    value("意识", String(format: "%.4f", spirit.entity.signature.consciousness))
                    value("自洽", String(format: "%.4f", spirit.entity.signature.coherence))
                    value("熵", String(format: "%.4f", spirit.entity.signature.entropy))
                    value("状态", spirit.entity.status)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private func cycleBlock(_ cycle: PrimalCycle) -> some View {
        GroupBox("八阶段") {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(cycle.steps, id: \.order) { step in
                    Text("\(step.order). \(step.phrase) · \(step.actionAxis) · \(String(format: "%.3f", step.nextIntegrity))")
                        .font(.system(size: 12, design: .monospaced))
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func value(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label).fontWeight(.medium).frame(width: 62, alignment: .leading)
            Text(value).foregroundStyle(.secondary).textSelection(.enabled)
        }.font(.system(size: 13))
    }
}
