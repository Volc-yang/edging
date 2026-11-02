# I15 执行登记：公开 proof 回放与只读能力采证

2026-11-02；状态 **partial，停止路径已独立结算**。输入/方案 `ee138ae`；[审定树及 v2/v3 裁决](design/universe-i15-proof-capability-plan.md)。七份任务/纠正 PR 已审查、最终 CI 成功并合入 `codex/plan-consolidation`；实际 Native 尚未运行，G-B2 未过。下轮入口在本页末尾，不需要重做已接受工具。

| 节点 | worktree / branch | 当前交付 / Check | 下一步 |
| --- | --- | --- | --- |
| N / i15_native | `.worktrees/i15-native-replay` / `codex/i15-native-replay` | PR115 `1872a91` → `274d090`，CI41439049209 success；root 13新+21旧 CPU 通过 | 工具接受；真实 Native 语义门未验证 |
| P / i15_probe | `.worktrees/i15-readonly-probe` / `codex/i15-readonly-probe` | PR116 `48ba395` → `e51dcf8`，CI41439556996 success；root 12新 CPU，owner43含旧回归 | 源码/准备接受；可见 probe 未运行 |
| P 纠正 | 同 P | PR119 `a29c3e5` → `d648bed`，CI41441093823 success；N独立14 CPU通过 | RHI依赖与实际 lib 文件名；build2验证链接成功 |
| C / i15_controller | `.worktrees/i15-capability`，最终分支 `codex/i15-controller-observer-ready` | PR117 `f50d627` → `6825f04`，CI41439782359 success；root12 CPU含真实child/timeout | 初实际 pre-dispatch observer缺陷，保留失败 |
| C 纠正 | 同 C | PR120 `89f66fc` → `5a6cca0` / CI41441120674；PR121 `a625798` → `077548e` / CI41443309316，均success；N独立最终16CPU通过 | 真实lib路径、skipped/noPID回调、实际首样本与失败stop/join；新控制器尚未实跑 |
| R / root | `.worktrees/i15-integration` / `codex/i15-integration` | PR118 `58f1baf` → `e52e4b8`，CI41439859086 success；N独立审查；6新+8旧 CPU | 真实CLI parent wait2，异常退出码正确 |
| M / X / T | root唯一运行owner | M环境缺证skipped；X旧3原始请求/响应准备成功；T pre-dispatch拒绝后预算预留不足skipped | 未消费实际UE窗口，不补造结果/正常会话 |
| A | N独立停止路径审查，root结算 | 原报告提交d00e243，等价独立review集成2b08441；39项原件索引 | 结算complete，父节点partial，不授G-B2 |

报告：[N](evidence/universe-I15N/report.md)、[P](evidence/universe-I15P/report.md)、[P纠正](evidence/universe-I15P/correction-report.md)、[C](evidence/universe-I15C/report.md)、[observer纠正](evidence/universe-I15C/observer-ready-correction.md)、[R](evidence/universe-I15R/report.md)、[A独立结算](evidence/universe-I15A/report.md)。原件索引：[39项公共原件](evidence/universe-I15R/runtime-evidence-index.json)。不含 owner 原文或 key 内容。

## 资源与验收边界

新独占准备 root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe` 已由审定 P helper 完成默认 audit 后显式独占创建；preparation SHA `0a3eadac82a5b9152e2310b37c206db97efc3e5a1ff61553a4f3bdd841215f49`。产品构建树 `.worktrees/i15-native-build` 固定初始 source `e51dcf8`；工具树与产品树分离。

首次官方 CPU build 实际 parent wait **exit6**，32.628994125s；arm64链接缺 `_GDynamicRHI`。原件 `prep/build-console.log`、`prep/build-raw.json` 及初始 preparation 不覆盖；已用独占 corrected preparation 绑定新源。后续成功不能抹去这次失败。

**执行环境修订 v2：**当前工具目录无 CUA，node REPL 实测 `cuaAvailable=false`。按方案新增明确 `skip_metal` 分支，M 标为环境缺证/未执行；若代码审查、构建与卡校验通过，可执行一次 Native 验证旧三个原始 proof。C 负责 typed 跳过证据与拒绝测试，root 复核；没有授权改用其他界面注入工具或将 skip 写为 pass。

本轮不初始化/prepare/advance/physics/retry；派生 owner 必须 existing / can_initialize=false / allowed_actions=[]。继承 r4 权威只读，不读 key 内容、不迁移或重置。标准双会话与 G-B2 仍未通过；旧 I12 2566/1200s fail、I13/I14 partial 及全部原件继续保留。旧 blocked goal 未改状态。

## 实际构建与首个控制器中止

PR119 `a29c3e5` → `d648bed` / CI41441093823 success；PR120 `89f66fc` → `5a6cca0` / CI41441120674 success，经 N 非 owner 审查。修复 RHI 直接依赖与实际 Mac lib-prefixed 产物定位。官方 build2 准确 source `5a6cca0`，parent wait0、6.841072875s；两次累计39.470067s<180。`prep/build-receipt.json` SHA85988e89bce7f6f4d0327a27dde58947f970664c3b5c9c2dc19a8ed399cbc6d2，原失败与 corrected preparation 分别保留；prepared 原件152f968c、old3 manifest1c17bf1a。N 独立核真实源码/二进制/RPATH/原始trace并放行能力专用 Native 路径，不是运行通过。

`capability/` 首 dispatch1182671.669250291；观察回调访问 skipped Metal 缺失PID，`start_native` 被拒绝，未创建 UE Popen。原 CLI transcript/requests/outer wait2 与 abort 原件保留；N独立核源/事件/目录及CPU复现，不称Native fail/pass。PR121虽已修复并通过CI，但到放行时，从首outer起的900s剩约187s，少于预设270s完整预留，**没有创建 attempt2、没有新prepared/card/manifest、更没有启动UE**。

`prep/campaign-resource.json` SHA `cd01220ccf0a597a5a730b7baa0e5c9cf666510d4e634269abab8dad3728f718`：从首outer1182671.312779333至seal连续 **771.427526s<900**，完整root实际bytes加16KiB保守封存余量 **1,471,501,078<2GiB**；结束无UE，权威before/after逐文件map相同。全周期observer在中止后有无法补回的间隔，门保持 **fail/inconclusive**。时长/字节有界不表示整体capability通过，亦不是UE性能测试。

## 下一轮唯一第一步 / 恢复与清理

从集成HEAD载入本登记与 A 报告，**直接准备准确source/tool和新预算卡后执行一次 old3 Native 回放**。成功产品/Native构建源保留 `5a6cca0`，最终修正工具源 `077548e`（后续纯文档提交不等于重新编译）；逐字节验证Native源与现有binary再决定能否复用，不无理由重建。新toolsource须绑定独占新prepared/card/Native manifest，旧case原字节继续引用，旧失败和中止不覆盖。无新需求时不继续增加框架、诊断功能或研究卡；先补实际四selector、三个case、正常wait和独立review。没有CUA就继续将Metal输入/PNG留待可用窗口。

构建树 `.worktrees/i15-native-build` / `codex/i15-native-build` 保留：prepared、source/binary审计与恢复入口仍引用它的源码/五个输出链接及批准ini，不能强删。N/P/C/R四个任务树均在最终交付、干净与提交保存、公共运行配置无引用核对后 **non-force移除**；[清理原件](evidence/universe-I15R/worktree-cleanup.json)记录路径/分支/HEAD，N独立报告逐字节等价集成后清理。所有分支、DevSSD原件、旧I12B与主checkout用户改动保留。没有合入本地主checkout；网站/DNS/API、UE引擎源码、crash-report发送及旧blocked goal状态未改。
