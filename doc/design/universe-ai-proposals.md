# U3：AI 提案与权限门设计

状态：v0.1 **proposed**，2026-11-01；parent=U，depends_on=U1。交付基线 `6f3c142aed2f67b556d87e2b649735e6c7fd4b2b`，U1 接受的 source `a7fed69` / merge `da84aba`。本文只提出版本化接口与检查设计；不修改现有 wire、worker、UE、世界规则或存档。

## Plan：范围与固定输入

**已定：**[U1](universe-identity.md)区分 World/Existence/Relation/Account/Session/Avatar，只有权威协调器可提交 head；[总树](../universe_architecture_design_plan.md)要求 AI 只提案；[G0](../pdca_g0_freeze_decision_record.md)将 AI 保留为总目标能力，非当前 V-HOME 必需门。Seed→Tree 是抽象因果发展；“万物有灵”不赋予模型任意写入权。UE5 发布版渲染与插件/适配优先，本卡无引擎源码需求。H6C 已接受的有限访客门不依赖本卡实施或模型可用性。

**代码观察：**[旧第一章运行时](../../engine/chapter_one_runtime.py)的 `ChapterOneRuleValidator` 校验字段集合、tick、动作轴与数值预算，`OllamaDecisionClient` 使用结构化输出，`_resolve_decision` 在模型拒绝/不可用后采用规则 fallback。可参考“输出先校验”的分层，不能将旧动作轴、2.5 总强度、八卦法则、模型 seed/temperature 或自动回退变成新宇宙规律。[S4](../seed_tree_genesis_slice_contract.md)只冻结工程物理探针，没有 AI proposal wire。

**本卡建议：**先允许 AI 提出一个已有、已批准命令类型的有限意图，不允许创建新规则、任意脚本、直接文件/工具调用或自行授予权限。内容生成、调参建议与未来世界动作分别声明能力；本轮只设计“单提案→至多一个权威命令”，复合计划另拆卡。正式动作清单、模型选择、预算数值和审批策略仍待冻结。

## Do：提案、权限和来源

下表均是 **候选逻辑字段**，编码、长度、规范化、错误码与持久化须由 U4 合成后冻结；它们不是现有 JSONL v1 的增补。

| 记录 / owner | 最小候选内容与约束 |
| --- | --- |
| `ProposalEnvelope` / AI 提案门 U3 | `proposal_schema, world_id, proposer_principal_id, proposal_id, base_tick, expected_revision, base_state_hash, observation_ref, intent_type, target_refs, parameters, provenance_ref, validity, budget_ref, proposal_digest`。principal 来自可信调用身份，不采信模型自报；目标 ID 必须在该世界与对应切片可解析 |
| 来源记录 / U3 | provider、model 标识及可获得的不可变模型 revision、提示模板版本、生成配置、输入观察摘要、原始输出摘要/工件引用、请求/完成时间、输出解析版本。provider 未提供版本时明确 `unavailable`；不得宣称相同模型名称保证复现。认证凭证不入提案工件 |
| `CapabilityGrant` / 权限策略；U6 提供身份映射 | principal、准确 world、可调用 intent/目标范围、有效区间、上限及 policy 版本；AI 不能改 grant。Account/Session 与 Avatar 的关系不作为隐式授权；化身是否已取得独立身份不由 U3 决定 |
| `ApprovalReceipt` / 规则或人工审批门 | proposal scope/digest、已解析命令摘要、policy/grant 版本、批准者身份/权限、决定及依据、审批有效期和撤销引用。模型的 rationale 是待审文本，不等于批准理由或因果事实；提交端只接受可从可信审批存储核对的 receipt（或验证受信签发），不采信客户端自造的 approved 字段 |
| `AdmissionRecord` / U3 与 U4 约定接口 | 校验结果、预算预留/消耗 receipt、审批引用、唯一 command 关联及拒绝原因；审计与预算账簿属于操作记录，不是世界 head。记录失败不得伪装成世界提交成功 |
| `AuthorityCommand` / 唯一权威 U4 | 经批准的 intent/目标/参数、proposal/approval 输入引用、固定 rule 版本、expected revision、目标逻辑时间、幂等 ID 和指纹；Genesis 候选仍按 U2 校验后进入规则转移，AI 不能跳过求解或伪造物理结果 |

**作用域与重复：**建议提案唯一键为 `(WorldId, proposer_principal_id, ProposalId)`；同键同规范化不可变 payload 返回既有受理状态，不再次生成/审批/执行。同键不同内容为冲突，即使原提案被拒绝也不覆盖原记录；修订使用新 ProposalId 并可显式引用前案。`proposal_digest` 覆盖所有影响决策的不可变字段及来源摘要，排除传输 `request_id`、重试时间和服务器状态。规范编码须拒绝重复 JSON 键、未知字段、非有限数、安全整数越界或不受支持的版本。

建议从提案作用域稳定派生 `CommandId`，例如域分离哈希 `H("ai-command.v1",world,principal,proposal_id)`；具体字节由 U4 冻结。一案只关联一个命令。指纹覆盖实际命令内容及 proposal/approval 引用，不把请求 ID 当幂等键。更换审批 receipt、参数或 expected revision 不得悄悄重用一个已执行提案产生第二次推进；内容变更须新案及重新审核。

## Do：有效期、预算与审批时序

| 门 | 设计建议 | 对重试与重放的影响 |
| --- | --- | --- |
| 逻辑有效性 | 默认要求 `base_tick/expected_revision/base_state_hash` 与准确已提交 head 相符；另声明可作用的 target tick/逻辑区间。不得默认 tick=revision，不能从渲染时刻推导水位 | 等待审批期间世界已变则拒绝旧案，重新观察后新案；自动 rebase/改 expected revision 禁止 |
| 墙钟有效性 | wall deadline 只控制实时受理/审批/提交前准入，不推进世界；可信服务端校验 UTC 时间与允许偏差。截止时刻、校验时刻和结果作为输入 receipt 保存；无可信时钟/不可判定不放行 | 已提交重试先返回原结果，不因当前过期倒转历史；历史重放用原已记录决定，不再次读取当前墙钟作同一转移的输入 |
| 权限 | 提案接收和临提交前都校验当前 grant、审批权限与撤销状态；输入文本不能改变能力范围 | 人工批准不绕过 schema/权限/版本/规则门。撤销后未提交案失效；已提交事件仍留历史，不事后改档 |
| 模型成本 | 预先限制输入/输出规模、超时、并发、重试次数及 token/费用预算；先预留再请求，记录实际消耗、取消与超时结果 | 被拒绝的生成仍可能花费模型费用，不能称“无成本”；超时不无限重试，不因模型故障自动推进 |
| 世界动作预算 | 和模型费用分开，审批 receipt 固定动作幅度/目标数等上限；所有数字单位、上限值由后续契约冻结 | 同提案重试不能重复扣世界动作预算；预算预留、提交与释放恢复关系交 U4 定义，结果不确定时停止新写入而非猜测重扣/退回 |

建议默认审批模式为 deny-by-default：只有 allowlist 中已批准动作才可进入审批。首个技术实现可用固定提案和显式人工批准；有版本化审批规则后可允许纯规则自动审批。两者都是候选开发方案，不预先把真人每次确认设为最终玩法，也不由 U3 批准新的宇宙法则。需要外部模型/付费调用的实施另须具体预算和运行授权。

时序（候选）：

```text
只读 Observe → 绑定输入/模型来源 → 受控生成或加载固定输出
 → schema/大小/版本/ID冲突校验 → world/水位/权限/预算校验
 → 人工或规则审核，生成绑定提案和命令内容的 approval receipt
 → 唯一权威串行化：先查已提交 command，再重检权限/期限/head/预算
 → Genesis与规则候选校验 → U4唯一事务提交 → 记录command结果
```

模型、提示词、提案文本和审批记录都不能直接写 manifest。提案被拒绝可写独立审计/费用记录，但 world manifest、状态/事件 head、已提交物理 checkpoint 引用必须不变；实现验收应分别比较权威文件与操作账簿，不把日志变化误判为世界变化。

状态机建议：`received → rejected | awaiting_approval → rejected/expired | admitted → committed/failed/uncertain`。状态只是受理元数据；`admitted` 不是世界提交。恢复先按稳定 command ID 查询权威结果：已提交则补齐 receipt 映射并返回原结果；未提交且确定失败才释放相应预留；提交结果未知则 fail-stop，由 U4 恢复协议核对磁盘，不能再次生成不同命令。历史 Observe 不触发此状态机或模型调用。

## Check：有界设计 fixture 与拒绝矩阵

以下均为 **设计正反例，未来运行状态 planned**。令 `W` 的已提交 head 为 `(tick=4,revision=7,hash=h7)`；调用 principal `P` 有已批准动作类型 `intent-demo?` 对 `E1` 的候选 grant。`intent-demo?` 是占位，不代表该动作/世界规则已获批准。固定归档模型输出 `O1` 和提案 `Q1`，不会调用模型重生成。

| Case | 输入或操作 | 设计预期 / 可判失败信号 |
| --- | --- | --- |
| P1 正例 | Q1 绑定 W/4/7/h7、O1 与 E1，schema/权限/预算和两种有效期均满足；审核 receipt A1 准确绑定内容 | 唯一权威以固定 C1 提交至契约允许的下一逻辑状态及 revision8，事件引用 Q1/A1/规则/物理候选。这里只检查引用闭合与权限时序，不声称发展数值正确；出现第二写者或未审核状态可见则失败 |
| N1 过期 | 墙钟截止已到，或逻辑目标区间已过；分别测试，保留可信时间 receipt | 拒绝新提交，权威文件集合/hash 不变；审计/模型账单可以变化。若只记录 expired 但 world 前进即失败 |
| N2 越权 | 模型自报管理员/另一个 Avatar，目标 E2 不在 grant，或审批者无相应批准权 | 拒绝；模型文本、身份别名或人工按钮均不能扩大 grant。若产生物理求解提交或世界事件即失败 |
| N3 同 ID 异内容 | 同 scope 的 Q1 改参数、来源摘要或水位，重发；另测不同 principal 使用同 ProposalId | 前者冲突且不覆盖原记录；后者是不同提案键但仍独立做权限/预算检查。若污染另一主体结果或二次推进即失败 |
| N4 非法结构 | 未知字段/重复键、错 schema、NaN、非整数 revision、超大 payload、任意脚本 intent | 明确拒绝而不派发命令；规范化不得把两份不同有效内容意外合成同一指纹。未拒绝或部分提交即失败 |
| N5 审批后变化 | 审批时 rev7，提交前 head变rev8；或 grant被撤销、receipt摘要与命令不符 | 临提交重检拒绝，不静默重基/放大参数。旧 receipt 不可替新命令背书 |
| P2 已提交重试 | C1 已成功但响应丢失，当前提案已过期；原请求同内容重发 | 优先查持久幂等结果，返回原已提交结果，无新事件/再次扣动作预算；不能以过期否认已提交结果或重新推进 |
| N6 未知提交/预算 | manifest替换结果未知、费用预留释放状态未知或进程中断 | 暂停相关写入并按 U4 恢复协议核对，不能凭超时假定未提交；若自动重发新 command 或无限生成即失败 |
| P3 重放与观察 | 用固定 O1/Q1/A1/原时间与权限决定及命令/规则/物理工件重放；随后多次历史 Observe | 不重新问模型/读取当前墙钟替代原输入；同版本同环境按已批准确定性范围对照摘要。Observe不调用模型、不改权威；模型再次输出相同不是本门前提 |

未来运行 Check 要固定 schema/policy/规则/预算值、时钟输入、代码/环境和 world 目录，保存完整提案/审批/命令/拒绝、费用与权威摘要。每个拒绝用前后权威文件映射比对；模型质量、动作是否有益、延迟/成本指标另立评估集，不以“JSON 能解析”判世界质量通过。

## Act 与 PDCA 交接

- **Plan：**读固定 U1/S4/G0 及旧第一章源码，区分已定原则、旧代码事实和新提案；不复用未批准的旧动作/回退法则。
- **Do：**本文件给出单提案至多单命令、来源与权限/期限/预算分层、准入状态机及正反例。未运行模型/UE/Genesis，未改产品文件。
- **Check（owner 自检）：**已核对 5/5 相对链接目标存在，工作区仅新增本文件；暂存差异格式检查通过。人工核对 P1/P2/P3 与 N1–N6 各有输入和可判失败结果，重复命令先查已提交结果，实时准入与历史重放分开。owner 自检不等于独立审查，非作者审查仍 planned；以上未来运行门均 planned。
- **Act：**交 U4 合成命令指纹、持久幂等、审批/预算 receipt 与事务恢复；交 U6 提供可信身份/会话及授权映射，交 U2 固定物理候选边界，交 U7 分离生成文案与权威事实显示。共享字段变更须父级审查，不能自行修改相邻设计。非作者审查通过仅解锁后续设计，不将 AI 变成当前 V-HOME 的必需运行门。

开放项：正式 intent allowlist 与产品规律、模型与版本可定位性、审批策略、可信时钟与允许偏差、预算/期限数值、审计保留和数据访问范围。未冻结这些项时只能进行无模型的固定提案协议实验设计，不能宣称生产 AI 权限、成本或演化验收通过。
