# PDCA-CHAOS-01 Subplan 任务卡

状态：规划任务卡；尚未发布实现 Agent。来源：`doc/chaos_universe_pdca_01_plan.md`。本文件的“通过”均指未来验收条件，不代表目前已经验证。

## 共同输入与派工规则

- **用户已确认：**初始混沌宇宙万象俱在，城市、蛮荒、原野、森林、海洋、河泽共同组成近乎完美的世界；万物之灵由 4D 演化显现；玩家的世界内化身属于世界之灵；空间不预设方块。
- **技术边界：**edgeWorld worker 是唯一权威写者；UE5 发布版负责观察与呈现；逻辑时间由显式提交推进；同 seed、规则版本与输入序列应可重建；历史观察只读。Genesis 仅在具体物理规则需要时接入，首轮 O1 不强制调用。
- **分支基线：**本轮规划工作树为 `codex/chaos-universe-pdca-plan`，起点 `d6298e3`。实现任务以主任务审定并提交 P0 契约后的**固定 SHA**作为共同基线，由派工卡填写；不得各自从移动中的分支取不同基线。
- **隔离：**实现 Agent 各用 `.worktrees/chaos-<task-id>` 与独立 `codex/chaos-<task-id>` 分支。既有 Seed→Tree PIE worktree、状态目录、未跟踪证据和主工作区未提交改动均为只读/不触碰。每项只提交所列路径，报告提交 SHA、实际检查、限制和 PR 或等效审查记录。
- **评审门：**先审定 P0 的语义与字段，再发布 D1/D2/D3；D4 等 D1/D2/D3 接口交付；C1/C2 在相应实现可运行后开始。任何共享字段变更先回主任务审查，再更新受影响卡片。

## 方案树与依赖

```text
P0 起源语义与共享契约 [主任务裁决；可交给一个规划 Agent 起草]
├── D1 混沌世界初态与生成 [subagent，可与 D2/D3 并行]
├── D2 CHAOS→ONE 权威演化 [subagent，可与 D1/D3 并行]
├── D3 UE5 混沌世界静态呈现 [subagent，可与 D1/D2 并行]
│   └── D4 UE5 固定状态观察接线 [subagent，依赖 D1+D2+D3]
├── C1 初态/因果/恢复独立核查 [subagent，依赖 D1+D2]
└── C2 真实画面与只读隔离核查 [subagent，依赖 D4]
    └── A1 主任务 PDCA 复盘与下一轮裁决 [依赖 C1+C2]
```

本轮最多同时运行 D1/D2/D3 三项写代码任务；P0 与 A1 的共享决策由主任务统筹。C1/C2 是独立审查，不由对应实现 Agent 自评为通过。

## Subplan P0：起源语义与共享契约

- **目标/交付：**冻结混沌初态、世界整体之灵、O1 首次分化、玩家世界内化身的定义；形成 `doc/chaos_origin_contract.md`（新文件），列明 Schema、命令、观察与失败语义。状态：待审定。
- **固定输入：**用户确认的起源设定；`doc/phase1_4d_prototype_contract.md` 的权威/观察边界；`doc/Seed-Edge-4D世界状态编码与演化评估分析报告.md` 为主工作区未跟踪只读参考，派工时须核对其 hash，不假设它存在于新 worktree。
- **所有权：**只写 `doc/chaos_origin_contract.md`；主任务负责修改方案树、backlog 和既有宇宙学文档的协调记录。不得提前改 worker 或 UE 源码。
- **执行步骤：**① 明确“世界形态已完整”与“灵域未分化”的可观测差异；② 给出 tick 0 manifest、区域/水系、潜势、O1 事件、固定时间 Observe 的字段和版本；③ 决定世界内居民的初始灵域语义及玩家化身何时取得身份；④ 将“随机、无主、无规律”转成可重放的运行边界；⑤ 列出 TWO/THREE/MANY 的开放接口，不编造数值规则。
- **验收：**一份可由 D1/D2/D3 独立消费的字段表与样例消息；相同概念不会在不同模块使用冲突身份；O1 失败不产生半提交；评审记录明确已接受与仍开放的决定。
- **风险/开放：**已有 `chapter_one_cosmology.md` 将玩家描述为外部变量，需把现实操作者与世界内化身分开；O1 的自然触发条件尚未确定。首轮可采用显式起源命令作可验证入口，不能把它宣布为最终宇宙法则。

## Subplan D1：混沌世界初态与生成

- **目标/交付：**按 P0 契约生成 tick 0 的规范世界清单与连续地理拓扑，覆盖六类场所和陆海水系。状态：等待 P0。
- **固定输入：**P0 契约的 Schema 版本、坐标/单位、区域 ID、生成 seed 与随机流规则；派工时记录共同基线 SHA。
- **所有权：**新建 `engine/chaos/world_generation.py`、`engine/chaos/initial_state.py`、`tests/test_chaos_world_generation.py` 和一个小型 `models/chaos/` 示例清单。不得编辑既有 `engine/world_engine.py`、树 worker、Genesis worker 或 UE 文件。
- **执行步骤：**① 构建单一连续样本区域的场所拓扑与河流入海关系；② 将地貌/聚落/生态潜势编码为权威数据，而非 UE Actor；③ 规范化序列化与 hash；④ 提供固定 seed/版本输出和错误输入处理；⑤ 记录规模与精度边界。
- **验收：**同 seed/版本多次生成相同字节/摘要；六类场所均出现、城市到河泽到海洋路径可追踪、水系不凭空断裂；不同 seed 的差异来源可查；不要求生产级城市或完整星球。
- **风险/开放：**视觉“近乎完美”不能由 manifest 自证；具体面积/精度须由 D3/C2 实测。不可把 8×8 卦域格直接设成混沌初态已确定的自然法则。

## Subplan D2：CHAOS→ONE 权威演化

- **目标/交付：**实现 O1 显式命令、单写提交、幂等、历史观察和重启恢复；不扩展 TWO/THREE/MANY。状态：等待 P0。
- **固定输入：**P0 契约的状态/事件字段；D1 的生成清单接口由 P0 规定，开发期间用契约 fixture，集成时消费 D1 实际输出。
- **所有权：**新建 `engine/chaos/origin_runtime.py`、`engine/chaos/origin_store.py`、`engine/chaos/origin_worker.py`、`tests/test_chaos_origin_runtime.py`。JSONL envelope 复用现有协议；若须改共享传输接口，先提变更给主任务。不得改 `engine/edgeworld_worker/tree_worker.py` 或 Genesis worker。
- **执行步骤：**① 加载并校验 tick 0 清单；② 处理带 command ID/revision 的 O1 请求；③ 原子提交 ONE 状态、因果事件、随机流位置和去重结果；④ 实现指定 tick/watermark 的纯读 Observe；⑤ 故障与重启路径只恢复最后完整提交。
- **验收：**同输入同摘要；重复 O1 不二次推进、同 ID 不同输入报冲突；前态/后态/规则/原因可查；历史观察不写 manifest；注入提交失败后无半状态；重启结果与不间断执行一致。
- **风险/开放：**P0 未确定的触发机制只能作为实验命令；不要把 Python PRNG 内部状态当跨平台稳定协议，须由契约声明算法/版本或记录显式抽样结果。

## Subplan D3：UE5 混沌世界静态呈现

- **目标/交付：**在 UE5 发布版构建一片连贯、可游览的混沌世界视觉样本，显示六类场所。状态：等待 P0。
- **固定输入：**P0 地理/场所字段和 D1 样例 fixture；仅消费数据，不自行决定区域身份或 O1。
- **所有权：**新建 `engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost/ChaosWorld*` 命名的场景/投影源码及其专属配置或文档；如需要改现有 GameMode/项目配置，由主任务先划定接入点，避免与未完成的 Seed→Tree PIE 工作冲突。不得提交自动生成 `DefaultInput.ini`、二进制地图或未经许可资产。
- **执行步骤：**① 盘点 UE5 发布版地形、水体、植被与程序化/模块化建筑能力及可用资产许可；② 固定一条城市→原野/森林→河泽→海洋的观察路线，保留蛮荒可见区；③ 从 fixture 建立场景；④ 记录镜头、光照、比例与加载预算；⑤ 对无法通过发布版能力实现的部分提供可复现缺口。
- **验收：**Editor target 构建；真实 RHI 可辨认六类场所和连续路线；场景逻辑不调用权威 Advance；截图、环境、资源来源与构建日志可复查。此任务的静态画面不等于 O1 4D 阶段门通过。
- **风险/开放：**“近乎完美”是艺术与体验目标，本轮先验可辨认、连贯和无明显断裂；城市复杂度、性能预算与资产许可须在实测后裁决。

## Subplan D4：UE5 固定状态观察接线

- **目标/交付：**让 D3 场景从 D2 的固定 tick/watermark Observe 样本切换 CHAOS 与 ONE 呈现，且只有用户明确操作才请求 O1。状态：依赖 D1+D2+D3。
- **固定输入：**P0 的 JSONL/Observe 契约；D1/D2 已审查提交；D3 场景投影接口。
- **所有权：**新建 `engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost/ChaosObservation*` 命名文件和相应 UE 自动化 fixture；现有 `EdgeWorldRuntime` 传输层只复用，若须改动先由主任务裁决。不得改树观察 Actor 或其状态目录。
- **执行步骤：**① 用现有异步进程传输连接独立 chaos worker；② 校验响应版本、tick、水位和 hash；③ 把已提交样本映射到场景表现；④ 提供显式 O1 与当前/历史 Observe 操作；⑤ 处理 worker 错误与关闭重启。
- **验收：**固定状态重复观察产生相同投影参数；UE 的 Tick、相机、帧率、暂停和显隐不会发送 Advance；错误水位显式失败；真实 RHI 能切换并展示 CHAOS 与 ONE。若仅有 NullRHI fixture，则保持真实画面门未通过。
- **风险/开放：**UE 内多个 demo 的 GameMode/环境变量可能冲突；必须为 chaos 使用独立启动参数、world ID 和 state directory。

## Subplan C1：初态、因果与恢复独立核查

- **目标/交付：**独立审阅 D1/D2 的契约符合性与实际可重复证据。状态：依赖 D1+D2。
- **固定输入：**P0 契约、D1/D2 精确提交 SHA、运行命令与隔离状态目录。
- **所有权：**只写 `doc/evidence/chaos-pdca-01/state-review.md` 和其小型证据文件；发现缺陷由实现 Agent 在原拥有路径修复，C1 不直接改实现源码。
- **执行步骤：**① 检查 diff 与生成清单；② 重复初态生成；③ O1、重复命令、错误输入和失败提交探针；④ 关闭重启并比较 state/event/manifest 摘要；⑤ 检查历史 Observe 纯读。
- **验收：**每项列明命令、版本、原始摘要和结果；失败可复现；未验证项标为开放。通过后只关闭规则/恢复门，不替代 UE 画面门。
- **风险/开放：**本机一致性不证明跨 OS/GPU 逐位一致；多写者和长期归档不属于首轮。

## Subplan C2：真实画面与只读隔离独立核查

- **目标/交付：**核查 D3/D4 的真实 UE5 画面、世界连贯性和观察不修改权威状态。状态：依赖 D4。
- **固定输入：**P0 契约、D1–D4 精确提交 SHA、独立 chaos state directory；不得复用 Seed→Tree PIE 的 Saved 状态目录。
- **所有权：**只写 `doc/evidence/chaos-pdca-01/visual-review.md` 与截图/日志清单；原始大型截图可放项目 Saved 并在报告给出路径/hash，是否纳入 Git 由主任务决定。
- **执行步骤：**① 启动单一 UE 项目实例并确认 chaos worker/PID；② 固定镜头采 CHAOS 与 ONE 画面；③ 逐项改变相机、帧率、暂停/恢复、重复 Observe、显隐；④ 每项记录前后 manifest/state/event hash；⑤ 对六类场所与连续路线做审查记录。
- **验收：**真实 RHI 日志和画面绑定到同一世界/tick/watermark；每个只读操作前后权威摘要不变；只有明确 O1 导致一次提交。缺图、白屏、未接 Worker 或未执行的操作不得记通过。
- **风险/开放：**已有 Seed→Tree PIE 因 Worker 环境缺失出现无效 Play；本轮启动配置与状态目录必须隔离并在日志证明。GUI 操作优先自动化，减少用户介入。

## Subplan A1：主任务复盘和下一轮裁决

- **目标/交付：**主任务逐项审查 P0、D1–D4、C1/C2 的报告与提交，更新 `doc/parallel_execution_backlog.md`，决定首轮通过/部分完成/失败，以及是否启动 TWO 的第二轮 PDCA。
- **所有权：**仅主任务修改方案树、统筹清单和决策记录；只集成已审查的任务路径。
- **验收：**每项 subplan 有工作树、分支、基线、提交、真实检查和限制；集成状态与任务分支状态分开记录；未通过门保留证据和下一动作；本轮上下文提交只含本轮范围文件。
- **决策依据：**世界视觉不足时改呈现；因果或恢复不成立时改状态机；UE 发布版有可复现契约缺口且插件替代失败时才评估源码。现有 PIE 迭代单独结算，不因本轮新计划而被宣布关闭。
