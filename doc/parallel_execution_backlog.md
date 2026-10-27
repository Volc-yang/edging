# edgeWorld 并行开发统筹清单

## 第一轮 PDCA：初始混沌宇宙（P 已完成，待方案审阅）

用户确认第一章起点是“天地玄黄，宇宙洪荒”的完整混沌世界：城市、蛮荒、原野、森林、海洋、河泽已经存在；万物之灵及玩家世界内化身的独立身份与因果关系由后续演化显现。空间表现不预设方块。总方案见 `doc/chaos_universe_pdca_01_plan.md`；任务卡见 `doc/chaos_universe_pdca_01_subplans.md`；工作树与精确状态见 `doc/chaos_universe_pdca_01_register.md`。P0 实验契约 PR #1、D1 初态生成 PR #2、D2 起源 Worker PR #3 和 D3 静态 UE 场景 PR #4 均已审查集成。seed 7 初态与 O1 黄金摘要、Worker 恢复/幂等、UE Editor 构建和 NullRHI 场景启动已有局部证据；D4 观察接线、C1 独立状态核查和 C2 真实 RHI/只读画面门尚未完成。D3 仍是 BasicShapes 代理，不将其称为“近乎完美”的最终美术效果。该新迭代不改变正在进行的 Seed→Tree PIE 阶段门或其 worktree。

日期：2026-10-10
状态：阶段 2 传输纵切已完成；A4D 单树演化算法实验原型已实现并通过定向测试。真实 UE 渲染、打包和跨平台阶段门仍未通过。

## 新迭代：第四维演化算法最小原型（完成）

目标：把 `doc/Seed-Edge-4D世界状态编码与演化评估分析报告.md` 中可检验的演化主张收敛成有限算法切片；先做 edgeWorld 权威逻辑原型，不改 UE/Genesis 集成边界。

```text
A4D 第四维演化算法
├── P 只读分析报告与代码并形成执行提案 [完成]
├── I 单树、确定性、逐 tick 状态转移纯函数 [完成：`04fe246` + `e316898`]
└── R 主任务审查算法假设、代码差异和证据后决定是否集成 [完成；统筹上下文已提交并快进主分支]
```

**已接受范围：**实验性单树模型；显式前态、环境样本、逻辑 tick 和版本化规则参数产生后态及可解释原因。纯 Python 函数，不使用随机数，不接入 Genesis、worker 持久化协议或 UE。生物量、健康、生命周期阶段和系数都是待审的实验参数，不升级为已批准世界规则。

**实现任务卡 A4D-ALG-01：**源码基线 `1d6444d`；任务上下文提交 `9891cc5`；实现 worktree `.worktrees/4d-algorithm`，分支 `codex/4d-algorithm-prototype`，子任务提交 `04fe246`、`e316898`。新增 `engine/evolution_4d.py` 和 `tests/test_4d_evolution.py`。输入分析报告仍是主工作区未跟踪材料，只读引用，SHA-256 `36a8291727affc658826023e5aa63c9d5eb7f31d8cd22ccb04ae441b21012422`；未复制/提交该报告，也未带入主工作区其他脏改动。`python3 -m unittest tests.test_4d_evolution -v`：6 项通过；`git diff --cached --check` 通过。审查修正超大整数输入会抛出意外 `OverflowError` 的边界。测试仅证明纯函数实验原型，不代表持久化、因果图、预算控制、Genesis 或 UE 阶段门通过。

**结论与后续：**算法/测试差异审查通过，当前为可审查原型，尚不升级为已批准世界规则。健康、生物量、水分、生命周期阈值及四象系数均未校准；尚无因果记录/快照接口，也未接入 worker。下一步由统筹评估是否批准规则语义及是否另开持久化/因果适配子任务。

## 新迭代：单 Seed → 树的 UE5 4D 呈现纵切（进行中）

目标：一个树种子按显式逻辑时间与环境规则演化为树；从固定 tick/watermark 查询 4D 状态，并由 UE5 发布版在生成场景中呈现；证明相机、帧率和 Observe 不改权威状态。

方案树（契约 `doc/seed_tree_4d_render_slice_contract.md` 已冻结为本轮实验边界）：

```text
A4D-2 Seed → Tree UE5 4D Render
├── C 主任务冻结 Seed/Tree 状态、环境输入、JSONL 与 SampleQuery 契约 [完成]
├── W 独立 tree worker：确定性萌发/生长、事件历史、精确观察、恢复 [执行中]
├── U UE 5.8.3：代码生成 PIE 世界、树视觉代理、固定时间观察呈现 [执行中]
└── I 集成 W/U：固定 tick 时间切片、真实 RHI 可见证据、呈现只读门 [待执行]
```

**接受决定：**树规则保持实验模型；一个树 Worker 与 Genesis 刚体 Worker/存档隔离，复用 JSONL v1 和既有 UE 进程传输；环境输入每次显式提供；观察水位必须精确匹配历史记录。UE 使用 Engine BasicShapes 生成地面/树代理/灯光/相机，不引入外部美术、不提交二进制地图、不改 UE 源码。具体契约、字段和阶段门见 `doc/seed_tree_4d_render_slice_contract.md`。

| 子任务 | 负责人/状态 | 代码所有权 | 依赖与验收 |
|---|---|---|---|
| T4D-WORKER-01 树种子演化 worker | 完成；worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/seed-tree-worker` / `codex/seed-tree-worker`；基线 `26947af`；提交 `5995d11`、审查修复 `845dfba`（集成为 `adef082`） | `engine/evolution_4d.py`、`engine/edgeworld_worker/tree_worker.py`、`tests/test_4d_evolution.py`、`tests/test_seed_tree_worker.py` | 确定性萌发/生长、JSONL status/advance/observe、幂等/水位/事件链/恢复；未改 Genesis `worker.py` 或 UE 文件。 |
| T4D-UE-01 UE 生成世界与树投影 | 实现完成；worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/seed-tree-ue` / `codex/seed-tree-ue`；基线 `26947af`、集成 worker `5995d11`；提交 `97d9372`、`9959ec1`、清理 `38e097c` | UE Runtime 观察 Actor/JSON client、Host GameMode/config、UE 自动化及 README | 冻结样本解析、BasicShapes PIE 场景和显式 Advance；UE 5.8.3 Editor 构建及 NullRHI fixture 通过；真实 RHI PIE 仍未验证。 |
| T4D-INT-01 端到端阶段门 | 部分完成；统筹提交 `ac9d5bc`、JSONL 探针记录 `58f67aa`、UE Host 模块启动修复 `716560c` | Worker/UE 集成、协议探针、阶段门记录 | Worker 阶段 seed→seedling→mature、幂等/只读/精确水位/重启通过；真实 RHI Standalone 成树画面已取得。PIE 与场景级状态隔离检查保持开放。 |

规划/实现任务基线为本轮检查点 `bdabc60`（代码祖先 `82d51ef`）。输入报告为主工作区未跟踪只读材料；子任务只读报告/已提交上下文，不接触主工作区其他脏改动，只集成任务卡拥有的路径。阶段门成功前，不宣称树生长规则已批准或完整 4D 引擎就绪。

### 本轮统筹与阶段门记录（2026-10-10）

**子任务收集与集成：**

| 子任务 | 结果与提交 | 验证与限制 |
|---|---|---|
| T4D-WORKER-01 | `codex/seed-tree-worker`，基线 `26947af`；实现 `5995d11`，恢复完整性审查修复 `845dfba`。新增独立 `tree_worker.py`，扩展 `evolution_4d.py`，新增演化/worker 测试。 | 16 项 Python 定向测试通过，`py_compile` 与 `git diff --check` 通过。恢复会核对状态重放、前态哈希、事件/历史字段、环境与原因、命令索引/指纹/结果。Genesis worker 未修改。仍为单进程单写者，规则系数纯实验。 |
| T4D-UE-01 | `codex/seed-tree-ue`，基线 `26947af`，集成 Worker `5995d11`；实现 `97d9372`、契约 fixture/README `9959ec1`、删除编辑器自动生成的 `DefaultInput.ini`：`38e097c`。统筹补充 `.uproject` 主模块声明修复 Standalone Game 的 GameMode 加载：`716560c`。 | UE 5.8.3 / CL 58210709 `EdgeWorldHostEditor Mac Development` 构建成功；NullRHI `edgeWorld.TreeObservation.ExactTimeSeedSeedlingAndMatureFixtures` 成功。Actor 无 Tick，重复同一样本的组件变换/显隐一致；覆盖 seed/seedling/mature、错误 tick/watermark、Advance 环境序列化。另在 Metal RHI Standalone Game 启动 Live Worker，日志观测 tick 5 mature，并保存画面到本地 Saved/Screenshots；PIE、相机/帧率/显隐前后状态摘要尚未验证。 |

**统筹端 Worker 探针：**使用真实 Python Worker 与固定环境序列，tick 0 观察为 `seed`，tick 1 为 `seedling`，tick 5 为 `mature`；重复 tick 5 Observe 响应相同且 manifest 字节不变；错误 watermark 返回 `watermark_mismatch`；重启新 Worker 后恢复到 tick/revision 5。另以真实 JSONL 子进程完成 `status → advance(environment) → observe` 并正常关闭。此探针与 UE NullRHI parser fixture 构成进程协议/解析证据，不等同于 UE Host 启动 Worker 的真实 RHI PIE 渲染。

| 阶段门 | 状态 | 证据/边界 |
|---|---|---|
| Seed → seedling → mature 确定性状态推进 | 通过（实验规则） | Worker 定向测试与固定环境端到端序列。参数未校准，不代表真实植物规律。 |
| 幂等、精确历史水位、Observe 只读、重启恢复 | 通过（单进程） | Worker/演化 16 项测试；探针验证重复 Observe 字节级只读、错误水位拒绝及 tick 5 恢复。未实现跨进程 writer lock。 |
| UE 固定字段解析与 BasicShapes 确定性投影 | 通过（NullRHI/fixture） | UE 5.8.3 Editor 构建成功；`ExactTimeSeedSeedlingAndMatureFixtures` 成功，源码与自动化检查 Actor 禁用 Tick。 |
| UE Host 启动 Worker 的真实 RHI 可见画面 | Standalone 通过；PIE 未验证 | UE 5.8.3 Metal RHI Standalone Game 使用 Host GameMode 启动 live Worker，日志记录 `Observed seed-7 at tick 5/revision 5 (mature, biomass 0.379, state_hash=4bbd13…e33de)`；截图 `engine_platforms/unreal/EdgeWorldHost/Saved/Screenshots/MacEditor/HighresScreenshot00000.png`。截图可见 BasicShapes 树冠和树干代理，但场景较暗、代理较简化。下一轮验证真正的 PIE 环境及 tick 0/幼苗/成树三个画面，并完善灯光/地面可见度。 |
| 相机、帧率、暂停/显隐不改变权威哈希 | 未验证 | 仅有相同样本重复应用的组件变换 fixture；未完成场景运行前后的 worker manifest/state/event hash 对照。与真实 PIE 证据一并补齐。 |
| Cook/package、跨 OS/GPU、复杂几何/生态真实性 | 未验证/不在本轮 | 仍属于契约中明确非目标或后续阶段。 |

**集成结论：**代码纵切已集成到 `feature/edge-world`。UE Host 真实 RHI Standalone 运行已显示 Worker 的成树观察结果；PIE 与场景级状态隔离阶段门仍开放。本轮记录为“Worker 与 UE 插件/Host 原型集成，Standalone 真实渲染通过，PIE/只读不变量部分未验”。UE 只消费 Observe 样本，演化仅由 Space 显式 Advance；没有证据触发 UE 源码修改。

**工作区边界：**本轮只纳入契约、Worker、UE Host/插件、UE README 与本统筹 backlog。原主工作区其他未提交/未跟踪改动全部保留，未纳入提交；Seed-Edge 分析报告继续仅作为只读输入。

**下一迭代入口：**获取 `feature/edge-world` 最新 worktree，载入本文与 `doc/seed_tree_4d_render_slice_contract.md`；优先完成 PIE 下 tick 0/幼苗/成树画面、提升树干/地面/灯光可见度，并做相机/帧率/暂停/显隐前后 manifest/state/event hash 对照，再决定是否扩展树形投影或演化参数。NullRHI/编译通过与本轮 Standalone RHI 证据分别记录，不互相替代。

## 上一迭代：阶段 2 worker-process 纵切

## 统一开发原则

1. 优先使用 UE5 发布版的成熟引擎与渲染能力，通过插件/适配层连接 edgeWorld 与 Genesis。
2. 以已批准的有限 4D 原型契约和可复现运行证据验收；草案和静态映射不算阶段门通过。
3. 仅在发布版插件/旁路方案对已批准契约出现可复现缺口且替代路径失败后，才评估 UE 源码改造；必须由统筹任务审阅缺口、替代方案、成本与许可影响。
4. 主工作区已有用户未提交修改，禁止 reset、clean、stash、覆盖或顺手纳入本轮提交；writing tasks 使用独立 Git worktree。

## 本轮目标与方案树

目标：集成 P1 UE Runtime 插件、P2 Genesis 公开 API 审计、P3 单刚体 worker，并补齐可实际启动的异步 JSONL 进程传输，验证最小 `status → advance → observe` 链路。

```text
I2 阶段 2 worker-process 纵切
├── R 收齐并审查研究/实现分支反馈 [完成]
├── I 按依赖集成 Genesis API 报告、UE 插件、worker [完成]
├── T 补齐 UE 异步进程/管道传输和响应解析 [完成]
├── V UE 5.8.3 + Genesis 1.4.3 live roundtrip/恢复验收 [通过]
└── G 更新上下文、提交检查点并前移主分支 [已完成：`354b5c9`，已快进 `feature/edge-world`]
```

## 子任务反馈与集成记录

| 工作包 | 状态 | 分支原始交付 / 报告 | 集成或验证结果 |
|---|---|---|---|
| 阶段 0 基线资产盘点 | 完成 | `codex/edgeworld-phase0-inventory` / `b338328`；`doc/phase0_edgeworld_inventory.md` | 研究报告留在分支，结论作为上下文输入；不代表现工作树全面验证。 |
| 主工作区改动审阅 | 完成 | `codex/edgeworld-dirty-tree-audit` / `47851f8`；`doc/phase0_dirty_tree_audit.md` | 只读审阅，无测试；报告留在分支。主工作区原改动已保留。 |
| UE5 子系统映射与发布版插件方案 | 完成（静态） | `codex/ue5-release-plugin-path` / `95a4e82`, `85a57a8`；两份 `doc/phase0_ue5_subsystem_map.md`、`doc/ue5_release_plugin_vertical_slice.md` | 方案报告留在分支；本轮后续改用 UE 5.8.3 安装版进行实际插件构建和自动化运行。 |
| 原型契约与许可边界 | 完成（有限原型契约已采用；商业归类未决） | `codex/edgeworld-license-boundary` / `58d3f4a`, `ce39e53`；契约草案、`doc/ue_license_distribution_questions.md` | 许可报告留在分支，非法律意见；生产契约/许可结论仍开放。 |
| P2 Genesis 公开 API 审计 | 完成 | 原提交 `363d23b`；`doc/genesis_public_api_audit.md` | 集成提交 `e70badc`；公开 `rigid_solver.set_gravity`、`Scene.step` 和 checkpoint API；探针范围为单自由刚体、Metal。 |
| P1 UE Runtime 插件 | 完成 | 原提交 `326c113` | 集成提交 `0738569`；本轮增加进程传输、紧凑 JSONL、响应校验及 UE 自动化用例。 |
| P3 Genesis worker | 完成 | 原提交 `2557ad2` + 修复 `e143c23`；`doc/stage2_worker_protocol.md` | 集成提交 `3b62331`、`fd9fb48`；保留单世界/单写进程、Genesis 1.4.3、Metal/macOS 的实验边界。 |
| edging.cloud 主页 | 已发布，DNS 验证待完成 | 站点源码提交 `e358fba`；`doc/edging_cloud_homepage_plan.md` | 主页已部署；`www.edging.cloud` 在 Sites 仍为 pending，验证 TXT/CNAME 尚未配置；不属于引擎迭代关闭门。 |

### 本轮集成实现

- UE `FEdgeWorldProcessTransport` 异步启动 Python worker，串行化请求，管理 stdin/stdout/stderr 管道、响应 request ID/协议版本校验、超时和进程清理。
- `FEdgeWorldJsonlClient` 使用紧凑单行 JSON，并拒绝超出 IEEE-754 精确范围的 tick/revision（`2^53-1`）。
- 新增 UE 自动化用例覆盖首次状态、推进、幂等重复命令、两次只读历史观察、manifest 不变及 worker 关闭重启恢复。
- `AEdgeWorldObservationActor` 仍禁用 Tick，只应用已提交观察结果；本轮用 NullRHI 自动化验证 worker/只读查询，未验证实际渲染帧输出。

## 阶段门与证据

| 阶段门 | 状态 | 证据/限制 |
|---|---|---|
| UE 5.8.3 插件 `EdgeWorldHostEditor Mac Development` 构建 | 通过 | 安装版 UE 5.8.3 / CL 58210709，Build.sh 成功。 |
| UE→worker→Genesis 实际 `status → advance → observe` | 通过 | `edgeWorld.WorkerProtocol.ProcessRoundTripRecoveryAndReadOnlyObserve` 自动化测试通过，退出码 0；使用当前隔离 Genesis 1.4.3 Metal 环境。 |
| 幂等和只读观察 | 通过 | 重复相同 command ID 后 tick/revision 保持 1；两次 observe 前后 `world.json` 字节一致。 |
| worker 进程重启恢复 | 通过 | 新 worker 进程从 checkpoint/manifest 恢复至 tick 1、revision 1。 |
| worker 持久化故障注入 | 通过 | `test_commit_boundary.py` 2 项通过，覆盖 manifest replace 和目录 fsync 不确定状态 fail-stop/restart。 |
| UE Actor 实际投影/Renderer 输出 | 未验证 | 静态确认 Actor 无 Tick；自动化采用 `-nullrhi`，未启动真实关卡验证帧/相机行为。 |
| Cook/package、其他 OS/GPU、并发多写、复杂 Genesis solver | 未验证 | 不属于本轮已证明能力。 |

## 仍然开放与下一轮入口

- 阶段 2 **传输和 worker 纵切任务关闭**；更大的 UE 呈现阶段门仍开放，需单独在 UE 5.8.3 真实关卡中验证 `AEdgeWorldObservationActor` 投影和帧率/渲染对权威状态的隔离，再决定 cook/package 范围。A4D 单树实验不替代该门，也未改动 UE/worker。
- 当前 worker 仅支持 macOS/Apple Silicon Metal、单刚体、单进程单写者；没有跨进程 writer lock。`view_spec` 只校验并回显。长期 tick 整数编码需在逼近 `2^53-1` 前升级协议。
- 当前 UE client 要求宿主显式创建 `FEdgeWorldProcessTransport` 并设置 Python、worker script、state directory 和 world ID；没有 Project Settings UI 或自动启动 Subsystem。
- P0/P1 研究报告仍保留在各自原始分支；已列出的 stage2 报告/实现已纳入本轮集成分支。未经后续审查的原分支不视为关闭或删除。
- 生产级时间/调度契约、跨平台确定性、通用状态迁移、复杂物理 solver 恢复、性能/规模和 UE 许可分类仍开放。没有证据触发引擎源码修改。
- 网站 `www.edging.cloud` DNS 状态独立跟进；保留现有 `api.edging.cloud` 路由，不代用户修改 DNS。
- 下一轮从当前统筹分支、本文、4D 执行计划、阶段 1 原型契约、A4D 子任务提交/报告及仍开放的 UE 呈现门恢复；主工作区其余未提交改动保持原样。

### 真实渲染展示续作记录（2026-10-10）

- **可展示证据：**UE 5.8.3 Metal RHI Standalone 运行截图 `engine_platforms/unreal/EdgeWorldHost/Saved/Screenshots/MacEditor/HighresScreenshot00005.png` 显示 Worker tick 5/revision 5 的成熟树观察。运行日志记录 state hash `4bbd13bb2befcc8b3c61bb1176afc48321644a583d9294955cc8fc9c6d2e33de`。这是 BasicShapes 的实验性视觉代理，不是植物几何；画面仍有黑天空、地面观感偏平以及一个未解释的异色球体，不能当作视觉验收完成。
- **状态只读观察：**演示前后 `tree_world.json` SHA-256 均为 `f529714e109b845e0118939316964faaa9eee1db78e7723b4dc1bee63c64c903`；tick/revision 为 5，state/event head 分别为 `4bbd13bb…e33de` / `440652d5…ce333`。运行/退出观察期间未见权威状态改变。发现多个孤儿 worker 进程共用同一状态目录后已停止它们；停止后没有遗留 worker。此项不替代相机、帧率、暂停和显隐各自的前后哈希对照。
- **采证限制：**命令行带 `-ExecCmds=HighResShot 2` 的游戏进程在 SceneViewport 报 `IsInGameThread()` 断言并崩溃，故不把该启动方式用于后续阶段门。截图可用于展示原型，但当前没有本次改动后的 PIE 截图证据。
- **下一轮第一步：**从 UE Editor 实际进入 PIE，固定并记录 seed、seedling、mature 三个观察水位；先修复天空/异色球体与地面观感，再分别对相机移动、帧率变化、暂停和显隐做 worker manifest/state/event hash 对照。PIE 与隔离门有实证前继续保持未通过。
