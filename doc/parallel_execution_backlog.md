# edgeWorld 并行开发统筹清单

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
