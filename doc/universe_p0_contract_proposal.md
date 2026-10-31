# P0 登陆场景与契约提案

版本：`universe-p0-v0.1`；日期：2026-11-01；状态：规划交付，待统筹审查，接口未冻结。

## 1. 任务卡与证据边界

- ID：P0；parent：U0；owner：P0 契约任务；审定 owner：总计划统筹；独立验证 owner：P4/U6。
- 固定输入：`b93f154`，统筹分支 `codex/universe-pdca-master`。总计划内的 `abc990a` 是其历史规划输入，本任务按委派使用包含总计划的 `b93f154`，不改写该历史。
- worktree：`.worktrees/universe-p0-contract`；分支：`codex/universe-p0-contract`；唯一写入文件为本文。运行时、其他任务提案、主工作区均不属写入范围。
- 目标：定义单区、单载具、单化身、单组持续对象的一次接近、登陆、出舱、游玩、离开与重访；多人、无限规模、跨机器确定性仍需后续契约。
- 已确认：现实操作者与世界化身分开；世界唯一权威写者；UE5 发布版负责呈现；Genesis 提供候选物理状态；渲染帧不是世界时钟。
- 本文所有新增字段、操作、阈值和状态均为提案。文档检查结果不代表登陆运行时通过。Google 理论旧对比未找到原始材料，标记**待核实**，不作为架构或验收依据。

| 证据 ID | `b93f154` 中的来源 | 已观察事实与适用边界 |
| --- | --- | --- |
| E0 | `doc/ai_4d_universe_pdca_master_plan.md`，总节点、U0、首批任务卡 | 总路径与 P0 所有权；U0 接口冻结是实施前置条件 |
| E1 | `doc/chaos_origin_contract.md` §1–6、§8 | Chaos 只有 tick 0/1 与显式 O1；place 是地理标识；个体灵域未决；整数厘米与精确历史观察 |
| E2 | `doc/phase1_4d_prototype_contract.md` §2–6 | 单刚体、单写者、候选物理与原子提交；生产时钟和离线结算未锁定 |
| E3 | `doc/stage2_worker_protocol.md`，Request mapping、Persistence | JSONL v1；每次 advance 只推进一个 tick；去重；提交不确定时 fail-stop；无跨进程写锁 |
| E4 | `doc/seed_tree_4d_render_slice_contract.md` §2–5 | Seed/Tree 独立身份、独立 worker/目录；显式环境；精确 tick/watermark；实验规则 |
| E5 | `doc/parallel_execution_backlog.md`，Chaos Realism、第二轮 PDCA、阶段 2 | 有限 Metal/只读证据；资产、真实帧时间、并发与跨平台门仍开放 |
| E6 | `AGENTS.md`、`doc/parallel_agent_workflow.md` §4–7 | 独立 worktree、显式所有权、子任务提交与统筹审查；发布版优先 |

证据定位采用固定提交与章节，避免把当前主工作区未提交文件当作本提案输入。E1–E5 是阅读到的历史记录，未在本任务重新运行实验。

## 2. 首条路线与身份生命周期

候选地点：E1 fixture 的 `plain-1` 内部，中心 `(35000,20000)` cm；登陆点必须由同源地形/碰撞数据验证后冻结。该 XY 在清单原野范围内只说明候选位置，不能证明地形坡度、净空或安全。建议首区 200 m × 200 m，步行路线 100 m、载具接近高度 100 m；均需 P1/P2 审查与 U0 冻结。

建议前置存档为已完成 O1 的同一世界；接近前用独立 `admit_avatar` 事件建立化身和载具结构身份，记录来源与控制授权。`avatar_id` 是可控制实体身份，`individual_spirit_id` 可为 null；是否允许尚未分化个体灵域的化身登陆由 D1 决策，未接受则阻止实施，不能借创建 Actor 绕过身份门。不将登陆事件解释为 TWO/THREE/MANY，也不改写 O1 的哲学含义。

| 身份 | 权威归属和生命周期 | 禁止的隐式替换 |
| --- | --- | --- |
| 操作者 `principal` / 会话 | 认证网关持有；授权票据映射到可控制 `avatar_id`；权威历史只记录不可直接识别现实账号的授权引用与策略版本 | 不把账号、相机名或 UE controller ID 写成世界之灵 |
| `world_id`、`place_id` | 从同源初态延续；新增 `timeline_id` 隔离实验分支 | 重访不生成新 world，不用显示名匹配地点 |
| `avatar_id`、`vehicle_id` | admit 事件创建；包含来源、姿态、控制状态、载具座位/化身所在空间；离开后继续保留 | Actor 销毁/流送卸载不等于实体消亡；重连不重生 |
| `individual_spirit_id`、`world_spirit_id` | 灵域语义由规则单独授权；结构身份不自动等于灵域；世界之灵沿用 O1 | 不给可见居民批量追认灵域 |
| `object_id`、`visit_id`、`command_id` | 对象跨 tick 稳定；每轮访问新 visit 关联同一化身；command 在 world/timeline 内去重 | visit/session/request ID 不充当实体 ID 或命令去重键 |

## 3. 步骤契约与逐步 PDCA

共同 Plan：先验证版本、授权、精确前态和唯一写者，再提交候选；共同 Do：本轮只给出下表规格。所有步骤的执行 owner 为未来 U5，物理依赖 P1/U3，呈现依赖 P2/U4，规则依赖 P3/U2，证据复核 P4/U6。S1 的前置为 admit 成功；`S1→S2→S3→S4→S5→S6→S7` 是无环顺序依赖，重访结束后可开启新的 visit；不是规划依赖图的回边。

| 节点 / Plan：输入与前置 | Do：候选命令、权威事件与后态 | Check：观察、证据与暂定门 | Act：未决与失败去向 |
| --- | --- | --- | --- |
| S1 接近；同世界 head、授权、化身在座位内；固定输入轴序列 | `pilot_input` → `vehicle_motion_committed`；姿态/速度按固定子步提交，阶段 `approaching` | E1/E2；未来记录每 tick 控制与轨迹，观察同源地形；暂定终点距候选中心水平 ≤20 m；观察无状态写入 | P1 冻结误差与控制范围；轨迹超界返 U3；地形错位返 U4；目前未执行 |
| S2 选点、下降、接地；`approaching`、安全点/接触面校验 | `select_landing_site`、`pilot_input` → `landing_site_selected`、`touchdown`；`descending→grounded`，保留接触面 ID | E1/E2；未来保存净空、坡度、碰撞轨迹；暂定坡度 ≤10°、接地垂直速度 ≤1 m/s、连续稳定 10 tick；无接触不得报成功 | P1/P2 冻结地形与接触语义；不安全时保持下降/拒绝选点，可显式 `abort_landing` 回接近；未执行 |
| S3 出舱；`grounded`、座位归属和出口净空 | `disembark` → `avatar_disembarked`；同一事务移除座位占用并设置化身世界姿态、`on_foot` | E1/E2；未来检查重试不重复实体、出口不穿透、位置与载具相连；暂定出口定位误差 ≤0.1 m | 出口/座位任一失败整笔不提交；D1 身份门未冻结则禁止实施；未执行 |
| S4 游玩；`on_foot`，可交互对象同水位可达 | `walk_input`、`interact` → `avatar_moved`、`object_interacted`；首例对一株规则对象施加显式浇水，记录资源扣除和环境变化 | E4；未来完成 100 m 路线和一次有效/一次越界拒绝；资源不得负值；对象下游变化有 cause 链；不宣称实验植物系数真实 | P3 冻结对象与资源规则、P1 定可达半径（候选 2 m）；规则不支持则返 U2，不用材质变化充作交互；未执行 |
| S5 离开；返回载具、可达入口、空座位 | `embark`、`pilot_input`、`end_visit` → `avatar_embarked`、`liftoff`、`visit_ended`；离区后 `away`，实体与对象不删除 | E2/E3；未来保存登舱/起飞/离区水位；候选离区距离 ≥200 m；座位与化身位置始终一致；断连不是 end_visit | P1 定起飞安全条件；断连采用版本化安全策略（候选零输入制动），不可伪造离开事件；未执行 |
| S6 离开后演化；`away`、持久 head、显式调度预算 | 调度身份发逐 tick `advance`，`world_evolved` 链记录规则/环境/物理；状态持续演化 | E3/E4；未来固定 100 tick，重启一次，对照不中断运行全部 state/event 摘要；禁止观察触发追赶 | P3 冻结环境序列与物理休眠条件；没有服务运行则重连前显式调度补算；闭式快进未获授权；未执行 |
| S7 重访；先确认补算完成，原实体和世界身份匹配 | `begin_visit` → `visit_started`，随后复用 S1–S3；`visit_id` 新建，化身/载具/对象 ID 延续 | E1/E4；未来对比离开与重访两个精确水位，至少一项规则对象标量有因果可解释变化；旧历史仍可查询 | 无变化检查环境/规则是否预期触发，不能补造事件；缺历史判 inconclusive；身份更换返 U1；未执行 |

S2 到 S3 之间未接地时出舱必须拒绝；S4 未在入口范围时登舱拒绝；S5 未登舱不得起飞；非法顺序不推进 tick、不改变持久 head。失败重试保留原 command ID 和原输入；新意图使用新 ID。

## 4. 权威、时间与命令接口提案

### I1 权威提交与接口所有权

Plan：唯一 universe worker 维护世界、载具、化身、对象和事件的一个提交序列。Genesis/AI/UE 只交候选或命令；所有权分别为 U1 权威、U3 物理、U2 规则、U4 投影、U5 集成。跨系统通过内容 hash 和同一事务关联；不能让现有三个实验 worker 共写一个目录。

Do：建议新隔离 schema `edgeworld.universe-landing.v1`，保存 `world_id, timeline_id, logical_tick, state_revision, event_watermark, initial_manifest_hash, rules/config hashes, entities, command_results, event_head, checkpoint_refs`。导入旧初态采用显式 migration 事件、源 manifest hash 与映射清单；旧目录和历史保持只读，旧 hash 不按新 schema 重算覆盖。发布持久 manifest 前完成所有候选/附件校验；manifest 是唯一提交点。AI 提案附模型/配方版本、输入上下文 hash、候选正文 hash，外部非确定输出作为显式输入保存后方可重放。

Check：E1–E4 为依据；未来故障注入覆盖物理成功后提交前、manifest replace 前后、响应丢失，恢复后不存在半个出舱/资源扣除事务；同输入重放摘要一致。Act：跨进程 writer fencing、复杂 checkpoint 恢复未实现，U1 必须先证明排他写入；否则阻止运行验收。

### I2 时间与离线调度

Plan：区分逻辑 tick、Genesis 子步、渲染帧、真实 UTC；一次成功 advance 恰好推进一个 tick/revision，事件水位按事件数量增长，不能再假定 watermark 等于 tick。候选 1 tick = 100 ms、10 个 10 ms 物理子步；由 P1/P3 联合决定，不继承阶段 2 的 8 子步为生产定案。

Do：命令进入版本化顺序的 tick 输入批；每个实体每 tick 最多一个运动输入，冲突显式拒绝或由冻结优先级裁决。UTC 仅供已授权调度器计算目标 tick，调度命令及基准时刻进入证据；演化内核只看显式 tick/输入。离开和关闭 UE 不暂停服务；关闭所有服务时不声称已实际算出未来状态。恢复后调度器逐 tick 结算，完成前返回追赶进度；Observe 只读现有已提交水位。

Check：未来同一 100 tick 输入序列，在渲染 30/60/unlimited、暂停、无 UE、重启情况下比较全部摘要；UTC 回拨不产生倒退 tick。Act：最大追赶预算候选每批 100 tick、每次运行 60 s；超时保存已提交进度并标 inconclusive，U0/P4 冻结吞吐阈值；不为达标改成静默跳 tick。

### I3 命令和查询

Plan：复用 JSONL 传输思想，新增语义先能力协商。建议 universe `protocol_version:2`，旧 v1 请求发往原 worker 仍保持原义；不假定当前 UE parser 能直接消费新字段。

Do：传输 envelope 为 `protocol_version, request_id, operation, world_id, timeline_id`；只读操作 `capabilities/status/observe`。写操作 `advance` 必含 `command_id, expected_revision, target_tick, ruleset_version, authorization_ref, inputs[]`；每项输入含 `actor_id, action, payload`。动作全集即 S1–S7 与 admit；AI 提案经规则校验后作为显式输入，不直接写状态。新增动作必须在 capabilities/schema 中声明，未知动作拒绝。

命令指纹包含所有语义字段和授权策略绑定，排除 request ID 与可刷新的传输凭证；去重键为 `(world_id,timeline_id,command_id)`。授权每次检查，已撤销权限不能借重放读取结果；授权有效时先查已提交相同指纹，再检查新的 revision。相同 ID 不同指纹报 `command_id_conflict`；过期 revision 报 `revision_conflict`；非法顺序/范围报 `invalid_transition/invalid_input`；权限不足报 `forbidden`，均无持久状态变更。调度器与玩家不能各自产生竞争性权威序列，由唯一写者排队裁决。

成功响应至少返回 `logical_tick,state_revision,event_watermark,state_hash,event_hash,initial_manifest_hash,events[],command_id`；每个事件含稳定 ID、类型、因果前驱、规则/输入 hash、相关实体、前后状态 hash。commit outcome 不确定时返回 `commit_status_uncertain` 且不返回虚构 head；fail-stop 后重启、status、同 command ID 重试确认结果，禁止新 ID 盲重试。

Observe 固定 `logical_tick`、`view_spec.watermark`、region/observer/resolution/error_budget/rules；返回精确匹配的 `source_revision`、实体样本、版本与摘要。历史、版本或水位不匹配显式失败，不回退当前状态。`watermark` 指事件水位，`source_revision` 指事务序号，字段不再混用。建议 tick/revision/watermark 改为无前导零的十进制字符串，未知协议拒绝，不让 UE double 隐式截断。

Check：未来覆盖重复、改 payload、撤销授权、旧 revision、错误水位/历史、超限整数与丢响应恢复；零重复提交、零未授权写入、零静默历史替换。Act：协议 v2、watermark 语义及升级适配需 D3 审定，冻结前 U1/U4 只能调查，当前代码不支持视为开放而非通过。

### I4 单位、空间与物理边界

Plan：权威空间先沿用 E1 整数厘米，Genesis 以米工作；冻结坐标轴、手性、重力方向、姿态与速度编码。候选权威 UE 轴约定 X 前/Y 右/Z 上，Genesis 由显式版本矩阵映射；角度/旋转采用待 P1 冻结的定点编码，禁止直接 hash 未规范浮点。

Do：适配器执行 `1 m=100 cm`、明确舍入/量化、固定子步；持久物理 checkpoint 与量化实体状态共同关联，下一步从已校验 checkpoint 续算，不能用渲染网格/碰撞代理倒推权威。地形碰撞源必须绑定同一初态及地形 recipe hash；UE 地形装饰不自动成为权威接触面。

Check：未来单位往返、轴向落体、定点边界与接地误差实验；暂定位置量化 ≤1 cm，跨单位累计误差与接触阈值由 P1 给预算。Act：不满足则调整适配/编码并递增版本；P1 复杂接触恢复证据不足时停在候选规格，不能沿用单自由刚体通过结论。

## 5. 与既有契约的冲突和裁决清单

每行是 P0 的子审查项，parent=P0，owner 为表内裁决人；Plan 为冲突识别，Do 为建议处置，Check 为未来验证门，Act 为决定前下游限制。当前全部是待审提案。

| ID / Plan：来源及冲突 | Do：建议处置 | Check：证据与暂定阈值 | Act / 决策 owner |
| --- | --- | --- | --- |
| C1：E1 §1–2/8 没有个体灵域；登陆需可控化身 | 分离结构身份/灵域，显式 admit，灵域可 null | 1 个化身、1 个载具；零账号直接入世界；来源事件完整 | D1，U0/规则 owner 确认准入时相；未决阻止 U5 |
| C2：E1 §3/5 O1 后禁止推进；登陆需更多 tick | 新 schema/ruleset，源世界显式迁移；不扩改旧 O1 | 原 tick0/1 历史 hash 100% 保留；迁移映射可追溯 | D2，U0/U1 审定；不把新步骤命名为 TWO |
| C3：E1/E4 watermark 与 revision 偶然同值；一 tick 多事件不再相等 | 显式区分事件水位/事务 revision；v2 adapter | 至少一 tick 两事件，错误水位必拒绝 | D3，U1/U4/P4 冻结；禁止静默兼容 |
| C4：E3 单自由刚体与 8×0.01 s；载具/角色需接触与步行 | 新物理 recipe、单位/接触/恢复预算 | S2/S3 轨迹与重启全覆盖，误差暂定见表 | D4，P1/U3；不足返物理节点 |
| C5：E1 整数厘米，Genesis 浮点米，UE 可变呈现 | 固定轴映射、量化/舍入和 checkpoint 绑定 | 单位往返 ≤1 cm 候选；禁止 NaN/无穷 | D4，P1/U1；编码未冻结阻止提交协议实现 |
| C6：E4 树 worker 与 E3 Genesis worker 各自权威 | 新 universe 单写事务包含规则/物理候选，旧目录隔离 | 故障注入后零部分交互、零双写 | D5，U1/P3；不把多个 manifest 当原子事务 |
| C7：E2 §6 离线与时钟未定；总目标要求离开持续演化 | 独立显式调度、逐 tick 结算、Observe 不补算 | 离开 100 tick 同机重演 hash 全等；真实吞吐待定 | D6，U0/P3/P4；缺证标 inconclusive |
| C8：E1 §3 JSON 安全整数；无限时间与多事件可能超限 | v2 十进制字符串编码，版本化升级 | 2^53−1、2^53、非法格式均有明确结果 | D3，U1/U4；旧 v1 上界保持 |
| C9：E3 无跨进程写锁；接入调度器可能双写 | 写者排他/fencing 作为 U1 前置，调度只是客户端 | 两进程抢同目录只允许一个写者；零双提交 | D5，U1；未实现不得开放第二写进程 |
| C10：E5 代理/相机导航已可见；登陆需可步入和物理净空 | 新角色/碰撞验收，资产/视觉门独立冻结 | 真 RHI 步行录像、同源接触面、CPU/GPU trace | D7，P2/P4/U0；导航成功不算可玩通过 |
| C11：E1 起源无随机 O1，AI 输出可能变化 | AI 输出内容寻址、规则验证、版本与采样输入持久化 | 同候选重放全等，至少一非法提案拒绝 | D8，P3/U1；未冻结不调用 AI 改世界 |
| C12：E0 Google 旧对比缺原文 | 待核实，仅保留背景项 | 原始文献/旧讨论定位、日期与逐条论断对照 | D9，统筹收证；不阻塞独立工程契约 |

## 6. 冻结门、集成证据与本轮 Check/Act

P0 的 Plan 是让 U0 可逐条接受、退回或延后 D1–D9；Do 为本文。规划依赖 DAG：E0–E6 阅读 → S/I/C 规格 → 统筹 U0 冻结 → U1 最小协议 → U2/U3/U4/U7 → U5 → U6。P1–P4 提案可并行；共享接口冻结前不启动其依赖实现。P0 本轮无代码或物理试跑预算；文档审查最多两轮，未决拆成具体 D 项返统筹。

未来集成 Check 以同一构建、seed、初态/规则/物理 recipe hash 运行 S1–S7；一轮人工操控与一轮固定输入重演，保留原始 JSONL、授权引用、事件、轨迹、checkpoint/manifest 摘要、相机视频、CPU/GPU trace。证据索引包含提交 SHA、工具/设备/OS/GPU 版本、UTC 起止、命令序列及每项 pass/fail/inconclusive；大文件保留在批准证据目录，仓库只提交索引和 hash。审查者为独立 U6，执行者为 U5。

不可让步的正确性门：身份唯一、写者唯一、授权失败零写入、幂等零重复、同机同配置重放摘要全等、Observe 前后 head/manifest 不变、非法历史无替代、恢复无半提交。S1–S7 的物理数值为候选，冻结前全部保留未决状态。目标硬件、分辨率、p95 CPU/GPU 帧时间、加载时间、视觉参考/rubric 由 D7 冻结：候选 1080p、p95 CPU/GPU 各 ≤33.3 ms、首区加载 ≤10 s，必须真实 trace；设置 FPS 上限或截图不作性能结果。预算和性能值未批准时只能报告实测，不能宣称达标。

本轮实际 Check（2026-11-01）：已读取 E0–E6；确认固定基线存在且独立 worktree 从 `b93f154` 建立；仓库主工作区含无关未提交内容，保持原状；路径范围检查、Markdown 表格列数、相对文档链接和 `git diff --check` 在提交前执行并以终端记录为证据。登陆、AI、Genesis、UE、离线、性能与故障注入均**未执行**，其结果为未验证。缺少旧 Google 原文的结论限于委派与 E0 记录，未声称完成外部检索。

Act：本文交付后请求统筹审查 D1–D9；D1–D8 中影响共享接口的决策需记录接受版本、owner 和证据，再形成 U0 ADR/实施卡；D9 可独立延期。若 P1–P4 提出不同时间/单位/实体语义，修订本文及受影响下游输入版本，不由并行任务各自隐式定案。规划 PR 合并仅表示文档接收，不代表契约已冻结或 U0/U5/U6 已通过。
