# edgeWorld 并行开发统筹清单

> 当前总计划入口：[edgeWorld 4D 数字宇宙集成开发总图](edgeworld_integrated_development_plan.md)。本文以下各节保留逐轮任务与原始验收记录；其中“未合入 `feature/edge-world`”描述的是当时状态。PR #25 已于 2026-11-01 合入远端 `feature/edge-world`（`383c72e`）。本地主工作区仍未同步且有用户未提交改动，不以远端合并代替运行验收。

## 当前入口：I 实现轮执行中（I10真实worker接受；I11B只读入口接受；I12可见门待验收）

总目标仍为持久AI 4D数字宇宙；Seed→Tree是抽象初态的因果发展。用户已批准I0–I12树并要求分配实现。集成branch `codex/plan-consolidation` / `.worktrees/plan-consolidation`，本地主工作区用户改动不碰。Goal旧“继续执行计划”blocked且API无resume，未冒称active。

| 已接受里程碑 | 准确结果入口 |
| --- | --- |
| U1–U9设计树 | [U9复核/原I0–I12树](design/universe-integration-review.md)、[U登记](universe_u9_execution_register.md)，仅设计接受 |
| I0–I7中性内核/静态物理及I0E契约 | PR77–85，G-C0.2格式/API及G-S1有限进程门pass；[I登记](universe_implementation_register.md)、[I0E/I6复核](design/universe-i0e-i6-coordination-review.md) |
| E1–E5 v0.2 blob/trust/commands/recovery | PR87–91，含finalCI/独立review/raw；[E1/E2](design/universe-e1-e2-coordination-review.md)、[E3](design/universe-e3-coordination-review.md)、[E4/E5](design/universe-e4-e5-i9-coordination-review.md) |
| I9 UE严格parser | PR86 / final0a905cf / mergee47065a，真实Build/StrictV02 NullRHI exit0，仅解析门；失败保留，[复核](design/universe-e4-e5-i9-coordination-review.md) |
| E6独立blob/trust进程门 | PR92 / final0ebd7b3 / mergeba7568c；89child/8真kill全部回收、finalCI全suite与root原件审查，G-S1.2有限pass；[报告](evidence/universe-E6/report.md) |
| I0A实际资产图 | PR93 / final572d4a4 / mergecb39e0d；9content/4native/352341B/0gap、root111raw+9actual files/DAG核验；仅editor-source，不是cook/许可/写实，[报告](evidence/universe-I0A/report.md) |
| E7 fixed support mass修订 | PR94 / finalbe951dc / merge52dd964；17CPU+oracle+UE实际StrictV02及finalCI通过；首测试TArray自别名失败保留，[记录](e7_support_mass_amendment.md) |

上述已接受任务的干净worktree均已核对后非force清理，分支/失败/DevSSD目标/原件保留。PR只合入集成branch，不表示已同步脏的本地主工作区或通过全部产品门。

**当前方案与owner：**[执行依赖细化](design/universe-runtime-execution-refinement.md)已由root接受，允许固定接口的CPU构造并行，真实门不变。

- I8已接受PR95 / merge51b95de：source9270349的post-build B/O与两臂/恢复/真实exit及root292raw+逐步FractionD核对通过，G-P1有限pass；首默认解析失败及全部原件保留。[I8/I10A复核](design/universe-i8-i10a-coordination-review.md)。
- I10完整接受：I10A PR96 / mergedcfd3bc；I10B PR98 / mergeb1c0371，真实初始化/retain/weak/strong/历史/幂等与worker双PID正常恢复通过，D−7/−48；root131+445raw/81records5roots3raw/32readonlypairs及finalCI复核，[最新审查](design/universe-i10b-i11a-coordination-review.md)。
- I11A PR97 / merge96466b5已接受CPU/build/Protocol/Strict/TransportRaw/实际synthetic exit evidence，finalCI/root审查；I11B PR100 / merge36d88ec已接受有限G-B1：真实五次只读往返/三proof与资产图/一次LookAt/UE与worker正常退出，root和u9独立核对89原件及全量不变maps；首次失败保留。[复核](design/universe-i11b-coordination-review.md)。legacy默认不改。
- I12：I12A工具准备已独立审查/CI接受并合入PR99 / merge971ed03（finalb3902be，sourceb5a5851）；首8mock及5定向、真实I10B离线子集通过，仅工具准备。[报告](evidence/universe-I12/runner-report.md)。实际运行未派卡；等解锁/R12与准确合并树后执行两UE会话/动作map/Metal原图/历史/恢复/真实退出，G-B2未通过。Mac当前锁屏，已异步请用户手动解锁；可见阶段在解锁与I11B通过后派卡。

owner-config/public-pins接口与typed36的明确分类、原件/资源总账见[I登记](universe_implementation_register.md)。S_records30、S_typed36、H≤64及资产A独立计量；旧U8初态≤32和G-Q不称通过。没有新域真实组合或写实产品门通过结论。默认网站/DNS与api.edging.cloud路由不变。

## V-HOME 可访问世界纵切（进行中）

UE 开发入口有限门已通过，沿明确 `--launch --viewport-preflush` 路径恢复 H6B；原默认关闭路径可靠性仍开放。总目标仍是可进入、观察抽象 Seed→Tree 因果发展、退出后重访的持久 4D 世界；Genesis 为必需路径，seed/tree 非植物。集成分支 `codex/plan-consolidation`，方案树见 [V-HOME PDCA](visitable_world_iteration_plan.md)。主工作区用户改动未触碰，UE5 发布版插件/适配优先，未改引擎源码。

**当前结果与资源：H6C 有限独立访客门已接受并集成，V-HOME 总门仍开放。**H6B PR #66 / `a2ae0f1` 的实现经 H6C @`f674483` 两次真实独立运行，source `4ae3148` / PR #69 / merge `0344827`，最终 CI 通过；[报告](evidence/home-visitor-independent-acceptance/report.md)和[统筹复核](evidence/home-visitor-independent-acceptance/coordination-review.md)记录安全出生、连续移动、真实墙栏阻挡/脱离、阈值恢复、Tab 保位、两模式 Space 0→1→2、逐项历史只读及同目录重访。35 个完整只读 pair、两推进 pair，455/455 原始哈希经非采证 reviewer 复算；人工鼠标复用 H6B 独立复核原件，非本卡新跑。两 UE/launcher 正常退出 0，未见本轮 reporter；构建/GPU 已释放。旧测试 Outer 错误及 reporter 自身 SIGSEGV 继续见[诊断](evidence/reporter-fixture-popup.md)，不判已根治。

| 节点 | 已审查集成 / 证据 | 当前结论与限制 |
| --- | --- | --- |
| 启动入口 | [预构建入口](ue_mac_launch.md) PR #58 / `507b9c2`；[真实 App PID 修复](evidence/ue-mac-launch-app-pid/report.md) PR #60 / `81bcd79` | 先构建所属 worktree 模块，直接监测 App 内二进制；初始化、有效 tick0、退出 0 已实测。Mac 上其他平台 SDK 提示不等于启动失败 |
| H1/H1a/H1b | [复现](evidence/g3-shutdown-isolation/report.md) #50 / `a421f78`；[无 worker 对照](evidence/g3-viewport-differential/report.md) #53 / `78fb890`；[组件差分](evidence/g3-component-differential/report.md) #57 / `6fbfd43` | `SceneViewport.cpp:196 IsInGameThread()` 为视口销毁断言，worker、因果 Actor/环境均非必要触发条件 |
| H1c | [相机目标差分](evidence/g3-viewtarget-differential/report.md) #59 / `c22e126` | 跳过 SetViewTarget 仍断言；92/92 原始哈希匹配。旧测试残留 reporter 已清理，用户截图不作为 H1d 新失败 |
| H1d | [无渲染线程临时路径](evidence/g3-live-safe-render/report.md) #61 / `3a38109` | 显式 `--no-render-thread`；两次完整 Genesis 会话/退出及恢复通过，12 项只读、120/120 原始哈希匹配；性能未测，默认模式不变 |
| H1e | [同步候选](evidence/g3-viewport-preflush/report.md) #62 / `b89c5f3`；[独立审查](evidence/g3-viewport-preflush/independent-review.md) | 默认关闭，A 退出 1/0、B 0/0；B1 reporter 干扰保留；40 项只读、396/396 原始哈希匹配。仅有限诊断实现 |
| H1f | [幂等修复与干净复测](evidence/g3-preflush-followup/report.md) #63 / `e6c9d96`；[独立审查](evidence/g3-preflush-followup/independent-review.md) | 修正后自动化 2/2；A/B/A/B 和两 B 边界样本退出均 0，19 组只读、同目录恢复、369/369 哈希通过。首次夹具 ensure 与 B3 工具限制保留；接受有限显式项目旁路，默认关闭。A 也全正常，不推断失败率改善或根治 |
| H-LIGHT-01 | [报告](evidence/home-runtime-lighting/report.md) #64 / `69cd400`；[统筹审查](evidence/home-runtime-lighting/independent-review.md) | DirectionalLight 明确 Movable；基线 16、修复 tick0/2/恢复均 0。四会话退出 0，最终接受 12 组只读、193/193 哈希；2 组损坏记录和污染启动排除。前后采用同一无渲染线程模式，不扩大默认线程可靠性 |
| H1g | [标准入口组合报告](evidence/g3-preflush-launch/report.md) #65 / `52c4c9a`；[统筹审查](evidence/g3-preflush-launch/independent-review.md) | 8 项 mock，两次真实脚本构建/退出 0，默认线程+显式同步、光照零计数、6 组只读与恢复通过，179/179 哈希匹配；接受有限开发入口。Buffer 原件与无损解码保留，不判根治 |
| HQ | [600 帧试采](evidence/gq-metal-sample/c3-report.md) #49 / `db20383` | GPUTime 598 个正值，p95 5.3435 ms，仅信号导出；旧计时不适用于临时执行模式，正式性能门 inconclusive |
| H2/H3 | [场景](evidence/home-causal-scene/report.md) #51 / `785b3ea`；[HUD](evidence/home-visitor-hud/report.md) #52 / `cb10df7` | 构建、Metal 独立检查及定向 NullRHI 通过，仍为 BasicShapes 技术代理 |
| H4/H5 | [组合运行](evidence/home-integration/report.md) #54 / `58362f4`；[独立复核](evidence/home-independent-review/report.md) #55 / `0c77e3d` | tick 0/1/2、Genesis 探针、HUD、只读、恢复有限通过；真人体验、UE 原始传输 JSONL 和正式视觉门未过 |
| H6A | [碰撞](evidence/home-walkable-environment/report.md) #56 / `f848c84` | 构建/NullRHI 胶囊体支撑与阻挡通过，因果代理无碰撞，真实步行组合现由 H6C 有限接受 |

以上已集成任务均经 CI/审查；所属干净任务 worktree 已清理，分支与 DevSSD 原始证据保留。H6C 有限任务完成；V-HOME 整体未关闭。可见退出可靠性子对话 `01a1952c-5012-76b2-9506-93ade84370b0`；可步行访客子对话 `01a1952c-73e3-7e13-89c1-8986048ea657` 已获恢复放行。

**阶段门：**V-HOME 未接受；默认线程原始路径可靠性仍 `fail/open`，当前仅有有限显式旁路。独立访客组合门已有限接受；G0 写实参考/性能阈值与 H5 完整真人体验仍待完成。每次运行记录真实进程、构建、Engine initialized、GameMode/Worker、有效观察、首张可见画面、异常时间和退出码；旧 reporter 与工具超时须按真实进程区分，不把 UI 调用返回当成运行通过。未获授权不发送崩溃报告。

## 抽象 Seed→Tree × Genesis 实现与 G3 集成（部分完成）

G3 [真实集成证据](evidence/stg-g3/integration-report.md)提交 `5c2190b`，PR #48/集成 `cd0283a`，CI 通过；任务 worktree 确认干净且提交已包含于集成分支后移除。原始证据保存在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-lxKhO5/`，索引 SHA256 为 `e6e912a3…0333b2a`。真实 Metal UE↔worker↔Genesis 的 tick 0/1/2、两相物理差异、重复命令幂等、历史/相机只读及重启恢复通过有限探针。点击窗口关闭按钮曾触发 `SceneViewport.cpp:196` 断言，第二次通过 ⌘Q 正常退出；**G3 部分完成，V-STG 总门未通过**。UE/Worker 已退出。[关窗复测](evidence/stg-g3/shutdown-recheck.md)在初始化后与因果场景稳定运行后各一次点击关闭按钮均以退出码 0 结束，未留下 UE/Worker；原失败未重现，间歇性退出门保持开放。原序列复现结果见本轮 H1；关窗按钮触发的旧归因已撤回。后续以最小差分试验定位窗口销毁原因，补 UE 原始传输身份记录与缺失的只读动作矩阵。G0 产品规律、写实视觉及性能阈值继续开放。

G2-AUTHORITY 新组合权威 worker 提交 `562b902`、恢复校验修复 `5603808`，PR #45/集成 `40bd7e8`；9 项定向测试和真实 Genesis Metal 两相探针通过。UE 按绝对脚本路径启动的导入问题另由 `495ccf7` 修复，PR #47/集成 `b70faa7`，10 项测试通过。G2-UE 抽象因果图、严格解析与键盘输入提交 `5ec7472`，审查修复 `2660fa9`、`0cfddd7`、`6a98b14`，PR #46/集成 `87732d3`；UE 5.8.3 Editor build、NullRHI 严格身份测试和 CI 通过。两任务均经非 owner 代码复审，干净 worktree 已移除。G3 已在其上完成有限运行验证，状态见本节。

## 抽象 Seed→Tree × Genesis 设计迭代（进行中）

用户确定下一版采用 Seed→Tree 且 Genesis 物理为必需路径，并进一步明确 seed/tree 是**抽象初态与因果发展结构**，不是植物实体。G0 范围与 [V-STG 方案树](seed_tree_genesis_pdca_plan.md)已据此修订；旧植物 Seed→Tree v0.1 仅为技术参考。S1 [单权威接口提案](seed_tree_genesis_interface_proposal.md)、S2 [UE 抽象呈现提案](seed_tree_genesis_ue_proposal.md)、S3 [独立验收提案](seed_tree_genesis_acceptance_proposal.md)的初稿 PR #36–#38 及语义修订 PR #39–#41 均已通过 CI/统筹审查，集成至本轮分支 `d607a6b`。这些是设计提案，没有新组合 worker、UE 场景或运行验收。统筹已合成 [S4 技术纵切实验契约](seed_tree_genesis_slice_contract.md)，经两次独立只读审查修正后，仅放行 G2-SCHEMA-FIXTURE：以中性 Genesis 探针和可复算 `influence_mm` 验证物理候选影响抽象发展节点；刺激不是世界法则。[G2 schema/fixture](fixtures/abstract_seed_genesis_v1.md) 经 PR #42 集成，消除初态哈希歧义；[Genesis 两相探针](seed_tree_genesis_counterfactual_probe.md) PR #43 在四个隔离 Metal 进程中重复得 `shaoyang=-7`、`taiyang=-35`，满足预声明差异，统筹复算原始哈希且独立 reviewer 接受有限技术门。新 [G2 实现卡](seed_tree_genesis_pdca_plan.md)据此放行组合权威 worker 与 UE 抽象投影并行开发；其后续实现和 G3 有限集成证据见上节。S0 产品拓扑/物理语义和视觉/性能阈值仍开放。

## G1 接口复核与 GQ 采样可行性（进行中）

补充：G1 [负例进程矩阵](pdca_g1_negative_probe_report.md)提交 `c56937b`，PR #34/集成 `72d4608`，树与混沌各 8/8 项返回预期错误码，拒绝请求前后持久状态文件哈希相同。首次混沌探针误配 world ID 的启动错误保留原始记录，随后在新状态目录重跑；统筹复算五份原始文件 SHA256 与报告一致。该任务 worktree 已确认干净、提交包含于集成分支后移除。**有限技术结论：**两类 worker 的成功路径、幂等、恢复观察和所列拒绝路径有进程证据；G1 产品接口冻结、UE 结果身份拒绝、Genesis、AI 和 GQ 帧时间仍开放。

从远端基线 `617eb5c` 继续。G1 [独立代码审查](pdca_g1_interface_review.md)提交 `8244328`，PR #29/集成 `29facac`：共用 JSONL envelope 存在，但原通用探针不能跨单刚体、树、混沌直接复用。G1 [v0.2 设计](pdca_g1_interface_design.md)提交 `6c7b1b6`，PR #31/集成 `4d3f8d2`，补齐分领域 fixture、错误映射与 UE 身份校验责任；第二次独立只读复核和 CI 通过。树/混沌各六步 `Worker.handle` 自检通过，进程 JSONL、重启、UE 和 Genesis 未在该设计卡运行，G1 接口仍未冻结。GQ [可行性报告](pdca_gq_probe_report.md)提交 `6c16a6f`，PR #30/集成 `2cea123`：本机工具文件与计时路径存在，但用户 UE/Worker 正运行，未启动第二场景，CPU/GPU 信号导出门为 `inconclusive`。G1 [进程探针](pdca_g1_runtime_probe_report.md)提交 `3d2f30a`，PR #32/集成 `8abc93f`：树和混沌各 9/9 次 JSONL 响应成功，重复命令结果、重启历史观察与已初始化后的只读文件哈希一致；初次 `status` 与状态文件创建重叠，该项归因未定。统筹复算五份原始文件 SHA256 与报告一致。四个独立任务 worktree 均已核验干净并移除。G1 仍需负例错误矩阵、UE/Genesis 必需路径和本版本范围裁决后才能冻结；GQ 待隔离运行窗口；G0 版本场景、AI/Genesis 必需范围和运行阈值仍待裁决。

## G0/G1/GQ 设计迭代（2026-11-01）

统筹基线 `5cac4a3`；集成分支 `codex/plan-consolidation`。总图见 [集成开发计划](edgeworld_integrated_development_plan.md)。G0 待决门见 [决策记录](pdca_g0_freeze_decision_record.md)，提交 `a1e14f1`：过程规划门已接受，产品范围、目标机与视觉/性能/可靠性阈值仍开放。G1 [接口设计](pdca_g1_interface_design.md)由 `codex/g1-interface-design` worktree 提交 `c742d0c`，PR #26 通过 CI 和统筹文档审查，合并 `0c22188`。GQ [证据与测量设计](pdca_gq_evidence_baseline.md)由 `codex/gq-baseline-design` worktree 提交 `631cdac`，PR #27 通过 CI 和统筹文档审查，合并 `b7a27a0`。两份设计的 Check 仅证明边界、证据字段和测量方案可审查；G1 实际探针、GQ CPU/GPU trace 和 G4 产品验收均未运行。G1/GQ 独立任务 worktree 已核验干净、确认提交包含于集成分支后移除。下一动作：裁决 G0 表中的场景/AI/Genesis 范围和目标环境，运行 GQ 短探针，独立审查 G1 共享字段后再冻结接口并发布必需 G2 叶卡。

## AI 4D 数字宇宙总计划（PDCA 规划与并行派工中）

用户明确本轮用 PDCA **规划和控制 4D 世界游戏的开发过程**，不由框架提炼游戏玩法规则。`doc/ai_4d_universe_pdca_master_plan.md` v0.2 以总节点 G、递归任务卡、G0–G5/GQ 开发 DAG 定义 Plan/Do/Check/Act；F0 递归框架 PR #22 与 F1 证据门 PR #23 已独立审查并集成，F2 编排见 `doc/pdca_f2_orchestration_plan.md`。G0 版本目标提案 PR #24 已集成；用户在 2026-11-01 确认本轮验收门通过并授权合并，故 G0 **过程规划门接受**。其具体运行质量阈值仍是待冻结的下游输入，不能宣称产品运行门通过。逐任务、分支、旧对话状态见 `doc/ai_4d_universe_pdca_register.md`。旧错误范围 PR #20/#21 已关闭。基线合并 PR #25 已合入远端 `feature/edge-world`，当前主工作区有用户未提交改动，合并操作仅更新远端，不触碰该工作区。下一步按拓扑发布 G1/GQ 规划与基准测量，并裁决 G0 提案第 4 节的数值门。旧 Google 对比原文尚未找到，不据此制定开发流程。

## 写实样区迭代 CHAOS-REALISM-01（技术纵切完成；写实美术与性能门开放）

以 `6697512` 为基线，统筹分支 `codex/chaos-realism-01`；方案树与逐任务状态见 `doc/chaos_realism_01_plan.md`、`doc/chaos_realism_01_register.md`。P1/T1/E1/L1 经 PR #13–#16 集成，主任务组装提交 `95601b6`。V1 的 PR #17 记录 Metal 蓝色空背景、权威只读隔离通过和视觉失败；T1-VF 的 PR #18 翻转地形/水面/路线绕序；V2 的 PR #19 在独立 Metal + Worker 运行中确认森林、河泽、海岸与路线可辨，tick 0/1 的相机/历史观察不改 manifest/state/event，只有显式 O1 推进状态。技术视觉链路通过，真实写实资产/材质和实际 CPU/GPU 帧时间仍未验证，不称为写实世界达标。原始画面/日志在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/`，Git 仅保留小型证据索引；当前迭代分支未合入 `feature/edge-world`，该工作区未提交改动未触碰。下一轮先确定授权资产与质量基准，再实现地表、水面、植物材质和实际帧时间采集。

2026-11-01 输入修复：写实样区原先只有 Space/0/1，无键盘镜头导航。新增样区专属 PlayerController，WASD/QE/方向键/Shift 控制观察相机，保留 Space 显式 O1 和 0/1 历史观察。UE 5.8.3 Mac Editor 构建通过；操作说明见 `doc/chaos_realism_01_assembly.md`。

2026-11-01 运行复核：用户所见旧进程仍从 `chaos-pdca-02` 启动 `ChaosObservationGameMode`，并未加载写实输入修复。已正常结束该旧 UE 进程，另从本统筹 worktree 启动 `ChaosRealismGameMode` 与独立 Worker。macOS 实际视口中点击聚焦后，长按 E、左方向键和 W 均使画面按预期改变；写实样区键盘导航已实测可用。当前新 UE 实例保留运行供用户操作。

## 第二轮 PDCA：混沌世界呈现可测性（A2 复盘完成）

以第一轮集成提交 `7cb65d2` 为固定基线，统筹分支 `codex/chaos-pdca-02`。方案树见 `doc/chaos_universe_pdca_02_plan.md`，完整 PR、提交和工作树记录见 `doc/chaos_universe_pdca_02_register.md`。H1 控制入口 PR #9、V1 六类代理 PR #8、C3 独立失败报告 PR #10、V1R 遮挡修复 PR #11 和 C4 独立复测 PR #12 均经审查与 CI 集成；C4 合并提交 `363c2de`。所有本轮任务 worktree 已清理，统筹 worktree 保留；主工作区原有未提交内容与旧 Seed→Tree PIE 工作树未触碰，迭代分支尚未合并到 `feature/edge-world`。

**阶段门裁决：**C3 在 UE 5.8.3 Metal、单 UE/Worker 下对 20 项相机、FPS 上限设定、UE Pause/Resume、显隐、历史/重复 Observe 和显式 O1 逐项记录 ack、manifest/state/event/head；仅 O1 改变权威状态，技术控制与已执行操作的只读门通过。C3 发现模板 OpenWorld Landscape 与 World Partition 流入遮挡森林、河泽、海洋和路线，视觉门曾失败。V1R 只在 Chaos 模板地图隐藏相应 Landscape；C4 从集成后的新进程独立复测，固定 seed7 下六类 BasicShapes 代理及 city→plain→forest→marsh→ocean 路线和河道可辨，镜头逐项不改权威摘要，故**固定代理可辨门通过**。证据见 `doc/evidence/chaos-pdca-02/visual-control-review.md`、`visual-retest.md` 及两份 JSONL 索引；原始大图/日志保留在主工作区 `Saved/ChaosC3Evidence`、`Saved/ChaosC4Evidence`。

**仍开放：**FPS=30 仅有引擎设定回读，没有实测 Metal 帧时间/cadence；BasicShapes 不达到用户期望的“近乎完美”世界美术，地形/生态资产及视觉验收标准未定；D3/D4 双次读取初态文件的竞态、macOS 限定 canonical hash、其他地图/OS/GPU、并发 writer 与生产规模未验。下一轮先定义视觉质量标准和资产预算，再分别安排帧时间计量、同源初态读取与跨平台哈希任务；未启动 TWO 演化。

## 第一轮 PDCA：初始混沌宇宙（技术纵切部分通过，A1 复盘完成）

用户确认第一章起点是“天地玄黄，宇宙洪荒”的完整混沌世界：城市、蛮荒、原野、森林、海洋、河泽已经存在；万物之灵及玩家世界内化身的独立身份与因果关系由后续演化显现。空间表现不预设方块。总方案见 `doc/chaos_universe_pdca_01_plan.md`；任务卡见 `doc/chaos_universe_pdca_01_subplans.md`；工作树、PR 与精确状态见 `doc/chaos_universe_pdca_01_register.md`。P0/D1/D2/D3/D4 和 C1/C2 均已通过独立 PR #1–#7 集成至 `codex/chaos-universe-pdca-plan`，最终 C2 报告合并提交 `72e52da`；未合并到主工作区 `feature/edge-world`。C1 有限单进程 Python 状态门通过。C2 Metal RHI 画面、显式 O1 和有限历史只读观察通过；相机、帧率、UE 游戏内暂停、六类场所连贯性和视觉质量仍未通过完整阶段门。D3 仍是 BasicShapes 代理，不将其称为“近乎完美”的最终美术效果。D4 canonical hash 核验限 macOS，初态文件双次读取存在竞态，本轮 C2 使用固定只读输入。该迭代未改变 Seed→Tree PIE 工作树或其阶段门。

**A1 复盘（2026-10-27）：**本轮判为部分完成：CHAOS→ONE 的固定 seed7 技术纵切可运行；完整“近乎完美的初始混沌宇宙”尚无六类场所连贯、视觉质量和全部呈现只读门的实证。C1 报告 `doc/evidence/chaos-pdca-01/state-review.md`；C2 报告 `doc/evidence/chaos-pdca-01/visual-review.md`，两张原始画面及日志留在主工作区 `engine_platforms/unreal/EdgeWorldHost/Saved/ChaosC2Evidence/`，未纳入 Git。C2 每项只读操作逐项比对的是原始 manifest SHA；state/event/head 在 O1 前后及矩阵结束解析，不能称为每项独立核验。所有本轮任务 worktree 均已清理，迭代集成 worktree 保留以供下一轮读取；主工作区未提交内容未触碰。暂不启动 TWO：下一轮先增加可自动驱动的 UE 相机/帧率/暂停/显隐测试入口，逐项记录 manifest/state/event，再逐区截图核验六类场所与路线，之后裁决视觉目标和 TWO 起点。

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
