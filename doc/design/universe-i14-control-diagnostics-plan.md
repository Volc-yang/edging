# I14 PDCA：真实只读诊断与版本化控制/验证

2026-11-02；parent I13/G-B2；root统筹。固定输入 `afb3f36ca70cfaad987f76bb44ce069a3a257de8`、[I13结算](../universe_i13_execution_register.md)、[I13接口](universe-i13-interfaces.md)。用户“继续”授权执行；本树经三个只读方案审查及root裁决后实施；实际状态见[I14登记](../universe_i14_execution_register.md)。保留旧I12 2566/1200 fail与I13 no-go，原件/世界/主checkout不动。UE发布版项目/插件优先，不改引擎源码或世界规则。

## 父节点 P/D/C/A

P：补上上轮确定的三项工程缺口：真实UE状态输出、R13控制生命周期、A/B/C最终证据组合。先冻结接口，再按排他路径并行，主任务串行接线和审查。D：三独立PR及root集成CLI/上下文。C：定向CPU/Native测试源码、独立review/CI；一次有界官方build仅证明编译，不当Native实跑。实际持键/PNG/时间/退出仍需独立卡，未ready不启动UE。A：失败只返工责任节点，缺证inconclusive；不把工具/编译成功当G-B2通过，V始终结算中止路径。

依赖DAG：`I14-0接口 → [I14-D诊断及动作v2 | I14-L控制及ledger.v2 | I14-V组合验证] → I14-R串行接线/编译/ready判断 → I14-S实机(仅ready后) → I14-A结算`。V验证模块开发与L并行基于冻结schema；实际验收依赖L集成，不能靠mock批准L。R no-go/S失败同样直达A，未运行下游skipped。

执行结算为partial/no-go；D/L工具与R接线已接受、V语义部分完成、S skipped，实际PR/检查/清理见[I14登记](../universe_i14_execution_register.md)。以下冻结任务卡保留，不将计划当结果。所有写任务从本计划冻结后的同一准确集成SHA新建 `.worktrees/i14-<slug>` / `codex/i14-<slug>`；独立PR目标codex/plan-consolidation，非owner审查后root合并。任务进度/PR/门分别记录，当前均queued/planned；不能由owner自授运行门。CPU定向测试、报告/差异检查允许；子agent不占GPU、不启动UE/solver、不读key、不provision。

## I14-D（owner验收agent；root审查；depends_on=0）

P：默认关闭的只读producer输出实际身份、状态、输入handler事件；同时以版本化B适配准确表达新增诊断查询和长call内事件。D独占：Host `EdgeWorldUniverseGameMode.{h,cpp}`、新增 `EdgeWorldUniverseDiagnostics{,Test}.{h,cpp}`（存在的文件按实际扩展）、`EdgeWorldUniverseActor.{h,cpp}`中仅只读投影getter；`scripts/universe_iteration/actions.py`及对应现有/新增定向测试、`doc/evidence/universe-I14D/`。不修改worker/authority/transport写协议或引擎源码。

启用仅显式 `EDGEWORLD_UNIVERSE_DIAGNOSTICS_V1=1` 且launch元数据run/source/session完整合法。run/source为启动卡声明，不能自证源码；真实host PID来自FPlatformProcess，worker/generation只缓存通过token/parser/observation+projection验证的回调；失效/reconnect立即清空。world/root来自Pins；trusted_head与selected_observation分开。身份未ready/busy/unknown时不输出成功marker。

新增只读Exec `UniverseDiagArm <action_id>`、`UniverseDiagReadback <action_id> <stage>`、`UniverseDiagDisarm`，白名单固定；不能接受PID/head/state/counters/rejected参数，不能调用status/observe/prepare/advance/reconnect。同步实际读取Camera/ViewTarget、投影getter返回的真实proxy集合及hidden、GetMaxFPS、IsGamePaused、显式preflush/实际viewport guard；无tick也可采pause。baseline必须来自实际对象；不偷偷舍入/恢复transform，不改变Space/R paused执行行为。

history拒写仅真实controller键绑定入口递增handler计数，记录是否处理/拒因；console不能冒充键事件。Space真实release与R真实release形成各自released读回，最终计数不变。held_history/held_current/released由真实Space事件、H原Latest→verified-current回调、实际release发出；提前松开就缺证，不补造。

B新增 `universe-i14-actions.v1` 分支，旧v1行为保持。新manifest明确包含每个DiagArm/Readback/Disarm的真实CUA调用；raw日志事件序号/偏移作为同一个长CUA chord调用内的有序处理证据，controller checkpoint时间仅为**读到事件**的时间，不冒充UE事件时间。不把一次调用伪造成三次。候选chord为现文档支持的pressKey组合+duration；顺序/持续能力仍待实际验证，不能离线宣称可行。相机原值不舍入，v2恢复容差暂定每轴≤1e-4度，同Camera/ViewTarget，变化需约15度；旧v1精确比较不变。业务20/5、全部readonly动作、拒写与恢复门不减。

C：Native测试源码覆盖默认关闭/坏配置/真实binding来源/epoch失效/handler计数/console不冒充/提前release/busy与pause同步读回；CPU负例覆盖single-call事件映射/全部新增命令计费/假事件与漏查询/相机超容差；非owner审代码、R官方build。Native未执行明确标未执行。A：producer或动作模型缺口保持no-go，只重开D，不捏造actual输入。

## I14-L（owner架构agent；root审查；depends_on=0）

P：真实R13版本化卡/控制状态机、独立observer、一次性许可及生命周期适配。D独占 `scripts/universe_iteration/dispatch.py`、`lifecycle.py`的**独立v2分支**、对应定向测试和 `doc/evidence/universe-I14L/`；shared runner由root接线。模块无UI操作；固定受审launcher/旧监督器由trusted Python backend接入，不允许JSON提供任意shell/callback/module名。

冻结卡格式 `universe-i13-r13.v1`：精确product/tool/launcher/原卡及manifest摘要、world/root/anchor、两session、private权限/有效期/execute、全局1200s及2GiB、显式每session阶段/输出。旧R12/v1严格逻辑不变；兼容内卡hash/映射须完整记录，不把旧subtotal冒称新全局账。正式validate必须复用旧validate_run或等价全部private pin/owner/Python链/源清洁检查，不只验证一份metadata。

控制API至少：validate card → persistent DispatchController；begin_session、record stage、register verified ready、permit(action_id,timeout)并消费seq、request_quit/ack_quit、record真实wait/finalize。observer独立于supervisor，覆盖global dispatch→最终seal，0.5s周期/≤2s gap。permit真实PID/start/argv、fresh log offset/clock/action绑定、≤10s且不跨deadline，单次使用/closing撤销，S2需S1同卡源正常completion和独立动作检查。quit_request只请唯一CUA owner正常退出，不替代实际wait；超时沿旧精确owned cleanup并normal=false。模块可提供CPU可执行backend，root接线后才暴露实际启动CLI；未接线或缺证必须拒绝execute。

ledger格式 `universe-i14-lifecycle.v2`：沿I13字段新增process.role=`runtime_core`或`build_descendant`、exit_status、build_parent_ref（core额外core_kind=launcher/ue/worker、session）；v1完全不放宽。core必须真实父wait/UE launcher实际wait/worker EOF-reap和同卡normal，未知/非0/force都不pass。build后代仅允许build阶段在同ps样本可追至批准launcher的真实后代；不能命中UE/worker执行入口或重新标记core；build_parent_ref必须关联pin launcher原始PIPESTATUS[0] build_exit_code=0及其阶段。其exit_status无实际wait只能null，完整保守区间/末样本消失仍必需，不声称它exit0。官方build结果不替代core实际退出。

最终charged-end使用明确保守上界并记录actual观察边界和验证完成未越上界；不能虚构精确封存时刻。全局连续墙钟不能由进程union替代；seal全部bytes/原件含自写账、观测缺口/污染不pass，unknown归属不kill。

C：真实受控CPU child可验证父wait及observer（不得UE/solver）；fake clock测试过期/错源/多attempt/第三会话/permit重放/PID复用/超时拒UI、S1fail拒S2、超出seal时字节上限、PPID1额外实例；v2合法build未知exit与core伪装拒绝，旧v1定向回归。A：任何未接的卡/生命周期环节报告partial，不生成可绕过的新runtime入口。

## I14-V（owner投影agent；root审查；depends_on=0，验收依赖D/L集成）

P：独立组合A ledger/B动作/C原PNG及既有authority/trace parser，杜绝label与原件脱钩。D独占 `scripts/universe_iteration/verification.py`、对应新CPU测试、`doc/evidence/universe-I14V/`；shared verifier由root接线。可单向import actions/capture/lifecycle；不可反向循环。共享parser以root固定代码callbacks注入，JSON不得选择函数，不能用任意callback自述pass授门。

API `verify_evidence(bundle_ref, *, expected_policy, authority_parser, trace_parser)`。expected_policy由外层冻结的source/card/run+两bindings、clock、public context/schema、manifest/capability reviews、ledger/executable/launcher/storage/public allowlist、每action/stage精确capture和actual退出绑定组成；不得从bundle自举expected。先public库存/实际hash，再A v2/B version/C核验，缺任一分量inconclusive、矛盾fail。两会话source/card/world/root/anchor相同、distinctPID/channel、S2无写操作；fake label不能代替真实observe/proof。

每action/stage capture必须一一消费、无重复/未认领；observation wrapper必须链接独立authority parser已重算的records_by_hash与trace实际request/response所选manifest及membership，而非任意verification_ref字节。schema/refs/membership/record内容不能只比head三元组；若某公开proof检查不能独立完成，明确inconclusive，不把callback的passed布尔当认证。复用旧inspect_authority/inspect_trace而不调用要求captured_at单点的旧verify_bundle；真实原PNG保留request→stable区间，来源/Metal最终仍独立review。

C：完整合成组合仅checks_complete_requires_review；有针对性的错source/card/clock、capture重复漏认领、proof与trace脱钩、records/hash/membership错配、非HEAD map改变、normalfalse/缺wait/extra trace、角色伪装、symlink/hash变与A/B/C缺证负例。A：保留未闭合的proof/来源/卡权限门，不伪造pass或新运行原件。

## I14-R / root串行集成与资源

三PR审查/CI后从准确集成SHA新worktree接shared runner/verifier，验证disabled默认及实际source映射，提交独立PR由非owner审。允许一次官方CPU build，单独记录上限180s/退出码/所有输出映射DevSSD（非实机global卡、不授Native/Metal门）；编译失败保留证据只重开D。子agent不得擅自build或起UE。

新增诊断查询是必需工作量，旧240s拟分配不足不能隐藏。I14新资源分配**提案待R审定**：global仍1200s/2GiB，S1 build60/start60/interaction360/shutdown40/seal20=540s，S2 build60/start60/interaction100/shutdown40/seal20=280s；共820，剩380明定最终封存180+异常/保守余差200，不授权额外attempt。此为版本化重分配，不延长旧失败窗口；D必须逐项证明新manifest≤各上限，持键/时间未知就no-go，不以更大上限当可行性证据。S1最迟480s quit、520s actual wait、540s seal；S2最迟220s quit、260s wait、280s seal。非ready不issue/dispatch卡。

最终A由非owner复核真实检查与raw，所有PR/缺口/清理/下一步压缩进执行登记并commit/push。UI仅CUA，退出后仅CLI；不改DNS/API、不发crash report、不触碰用户主checkout/I12B保留输出。实机、写实与整个数字宇宙目标均不由本工具轮自动接受。

## I14-0 冻结补充：L/V共用API与时间边界 v1

评审：验收agent与投影agent无阻断，架构agent提出的L/V数据接口缺口在此冻结；root接受。该补充不以未观测值授予runtime。

L必须导出：

```python
validate_ledger_v2(ledger, *, expected_policy, actual_finalized_monotonic=None) -> dict
```

结果status枚举 `fail / inconclusive / checks_complete_requires_review`。缺实际封存audit时inconclusive；不调用v1再patch预算。`expected_policy`精确shape：

```json
{
  "format":"universe-i14-lifecycle-policy.v1",
  "run_binding":{"run_id":"...","source_sha":"SHA40","world_id":"...","authority_root":"ABS"},
  "clock_id":"controller-domain",
  "accepted_executable":"ABS-UE", "worker_executable":"ABS-Python",
  "launcher_source_ref":{"path":"ABS","sha256":"SHA64"},
  "launcher_identities":[], "session_bindings":{"initialize":{},"existing":{}},
  "storage_root":"ABS", "public_paths":[],
  "global_limit_seconds":1200,"storage_limit_bytes":2147483648,"observer_max_gap_seconds":2,
  "sessions":{
    "initialize":{"max_seconds":540,"quit_after":480,"wait_after":520,"stage_seconds":{"build":60,"startup":60,"interaction":360,"shutdown":40,"seal":20}},
    "existing":{"max_seconds":280,"quit_after":220,"wait_after":260,"stage_seconds":{"build":60,"startup":60,"interaction":100,"shutdown":40,"seal":20}}
  }
}
```

identity/binding/ref/clock格式沿I13；空数组仅表示schema示例，不能当真实complete。public_paths是外部已批准公共allowlist，不扫描private自造。所有time有限秒（bool不算），UTC带时区。

v2沿用I13 ledger的run/clock/dispatch/samples/sessions/processes/seal，另明确：`charged_end_monotonic`为保守计费上界，`end_monotonic`必须等于它；`actual_observed_end_monotonic`为最终发布前最后一次真实controller观察，绝不称为“已完成最后写入”；`seal.ended_monotonic`为实际已知封存动作边界，`storage_snapshot.monotonic`为实际存储采样时刻，不要求二者伪装成charged_end。关系：dispatch ≤ snapshot.monotonic ≤ actual_observed_end ≤ actual_finalized_monotonic ≤ charged_end，seal.started ≤ seal.ended ≤ actual_observed_end，observer_end ≤ actual_observed_end，actual_observed_end-observer_end≤2s且最后样本无本轮存活进程。最终发布/核账真实结束 `actual_finalized_monotonic` 必须来自持续存活owner的独立audit/返回值，缺失或不能认证就inconclusive。最终bytes包含已发布ledger/receipt/snapshot自身固定点及所有本轮文件；写后元数据/计时检查若超上界不能pass。

process v2必需字段在I13基础上加 `role, exit_status, build_parent_ref`，core还需 `core_kind, session`；build_parent_ref为 `{path,sha256}` 公共wrapper，含真实launcher identity/session、原始launcher stdout ref及精确line byte range、build阶段范围，必须解析该原件中固定 `[launcher] build_exit_code=0`（pin launcher源码确为PIPESTATUS[0]）。runtime core由外部session bindings/launcher identities优先识别，禁止靠输入role自认。build后代真实同样本父链/phase/bracket必需。

V的 `expected_policy` 顶层固定包含 `format=universe-i14-verification-policy.v1, lifecycle`（上述完整shape）、`actual_finalized_monotonic`（独立audit时间）、`public_context, schema, manifest_ref, resource_card_ref, capabilities, session_expectations`；V特有每capture/observe关联schema由owner交付并root复核，L不得读取或修改V字段。V单向调用上述固定API，模块不可循环import。actual audit/source/card真实性始终由root额外审查，字段存在或callback返回passed不等于认证。

实际启动须由**一个持续存活的Popen owner**持有launcher至wait/finalize，并让独立observer跨两会话及最终封存存活。不得每次CLI重建对象后将JSON当父wait；未提供该实际后端时execute拒绝、交付partial。D的诊断启动环境仅从已验证R13卡映射白名单传给受审launcher，旧R12默认environment过滤行为不变。
