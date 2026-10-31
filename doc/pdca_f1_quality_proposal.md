# F1：递归 PDCA 的质量门与证据契约

状态：proposal。输入基线 `1f7e67e`；只定义**开发过程的 Check 与 Act**，不制定游戏玩法、物理或演化规则。父节点为 `GQ`，同时供所有 `G0–G5` 子树复用。F0 定义节点生命周期；F1 定义每个检查如何被观察与裁决；F2 负责派发和登记。

## F1 的 PDCA 任务卡

| 字段 | 内容 |
| --- | --- |
| Plan | 以既有 `serial-firmware-loop` 的可复用循环纪律与 Chaos Realism V1→T1-VF→V2 证据链为输入，定义自测、独立审查、集成三类门、统一 run 身份和三值结论；不复制串口、烧录或 ELF 机制。 |
| Do | 本文的证据记录格式、检查矩阵、阈值冻结与返工规则。实施脚本和各模块检查由后续叶任务负责。 |
| Check | 用真实历史链回放：V1 同时存在通过、失败、缺证；修复有独立提交；V2 重测只关闭受影响的技术视觉门，不误关写实/性能门。若格式无法表达任何一步，F1 提案未通过。 |
| Act | 统筹审查后接受、修订或拆分；未通过的字段返回本任务，不改变已保存的历史原始证据。 |

## 三级检查门

| 门 | 执行者 | 输入与方法 | 完成条件 |
| --- | --- | --- | --- |
| C1 任务自测 | 实现 owner | 在任务独立 worktree 对精确提交运行任务卡约定的构建、单元/行为检查，保存原始输出与环境 | 所有本任务必需项有有效结果；PR 描述列实际运行项和未测项 |
| C2 独立审查 | 非实现 owner | 审查 PR 精确 diff、范围和契约；在独立环境重跑关键行为或检查原始证据；视觉/交互须看实际画面或运行实例 | 审查记录包含逐门结论，重大缺口返工；PR 合并前不能仅凭 owner 声称通过 |
| C3 集成检查 | 统筹/独立验证 owner | 在合并后的固定集成提交检查接口与真实端到端路径；对比权威状态、可恢复性和资源负载 | 子任务通过加集成门通过才提升父节点；合并 PR 本身不等于 C3 通过 |

每张任务卡先声明 C1/C2/C3 的适用性和责任人。纯文档任务的 C3 可是跨文档一致性检查；没有运行时目标时不强加 UE 测试。高风险接口可要求两名独立 reviewer；不为常规小改动堆叠无意义验证。

## 每次 Check 的记录格式

```yaml
check_id: <node>/<gate>/<case>
threshold_version: <approved-version-or-provisional>
result: pass | fail | inconclusive
run_id: <unique-id>
owner: <executor-and-independent-reviewer>
subject: {git_commit: <sha>, build_id: <id>, input_hash: <sha>, config_hash: <sha>}
environment: {platform: <id>, tool_versions: <ids>, isolated_state: <path-or-id>}
window: {started_at: <timestamp>, ended_at: <timestamp>, timeout: <duration>}
method: <command-or-human-procedure-version>
raw_artifacts: [{uri: <path>, sha256: <sha>, size: <bytes>}]
summary: <measured-observation-and-limit>
decision: <reason-linked-to-frozen-threshold>
```

单条记录只引用原始文件；原始日志、图、轨迹、录像不裁剪覆盖，筛选摘要与它分存。意外退出保留已采字节。长时/大型产物可存项目批准的外部卷，Git 保留小型索引、哈希和必要的复现命令。摘要须可定位原始时间、行号或帧。敏感凭证不入 Git。

`pass` 要求方法实际执行、身份齐全、关键观测信号有效且满足预先冻结的阈值。`fail` 要求有效信号明确违反阈值或发现契约/实现缺陷。`inconclusive` 用于未运行、超时无关键输出、工具采样缺失、环境不符或阈值尚未批准；它不等于通过，也不自动证明实现有缺陷。单次 Check 可分维度结果，父门不能把其他维度的通过外推。

## 阈值、诊断和返工

1. G0 在执行前冻结本版本的必需门、输入、目标环境、量化阈值和判定方法；开放阈值可暂定但结果只能报告实测，不宣称总门通过。
2. 阈值或方法变更产生新版本与原因，保留旧版本及其结果；不得看见失败后回填旧阈值。环境变更要做可比性分析。
3. `fail` 时先固定完整现场，列**事实、假设、缺证**，再把可复现原因分配给最小 owner 节点。只重开该节点及其依赖下游；已独立通过的节点保持结果，但接口变更可能要求相关回归。
4. 修复用新提交、新 run ID 重测受影响门。原失败和新结果并列；不能改写旧记录为 pass。`inconclusive` 优先补采缺失信号，未证实原因前不盲改产品代码。
5. 每个循环设观察时长、重试次数和资源独占规则。用户现有实例、存档或其他任务资源不得为了强行通过检查而被覆盖。

## 历史链回放：V1 → T1-VF → V2

| 节点/精确证据 | 按本契约判定 | Act 影响 |
| --- | --- | --- |
| V1：PR #17 / `7dd9736`，DevSSD `Renders/V1`、`Logs/V1` 与 `doc/evidence/chaos-realism-01/index.jsonl` | Metal 和 Worker tick 0/1 链路 `pass`；相机/历史 Observe 不变更 manifest/state/event `pass`；地表/水面缺失 `fail`；实际帧时间 `inconclusive`；写实美术 `fail` | 保留原图/哈希；只给地形可见性重开 T1-VF，性能和美术留开放门 |
| T1-VF：PR #18 / `734bbdf`，合并 `93ee1a7`，DevSSD `Renders/Terrain/seed7_terrain_winding_fix_metal.png` | 独立地形预览显示绕序修复，UE 构建/CI `pass`；尚不能替代组装场景 C3 | 触发 V2 独立组装复测，旧 V1 结论保持可追溯 |
| V2：PR #19 / `6a84b3b`，合并 `3c8de2f`，DevSSD `Renders/V2`、`Logs/V2` 与 `retest-index.jsonl` | 地形/岸/水/路线可辨、只读隔离 `pass`；程序代理的写实美术仍未通过；实际 CPU/GPU 帧时间 `inconclusive` | 关闭“表面被剔除”的技术视觉故障；不关闭写实美术和性能门，不重开无关的权威协议任务 |

这段回放证明三值、分维度结论和局部返工足以表达真实开发史，也暴露了旧登记文末“组装场景仍待 V2 复测”已过期；统筹在下次上下文维护时应更正，避免登记表与叙述冲突。
