# I13-0 接口冻结 v1

父节点I13；2026-11-02；实现输入基线d763f589feede12e9d07a1cad04a6cc676e32362。统筹root；状态：独立审查通过，接口v1冻结（u9复审及root接受，2026-11-02）。方案见[I13](universe-i13-corrective-pdca-plan.md)。本契约用于控制/采证模块，不更改权威协议、G-B2或世界规则。

## 分层与所有权

- root维护本接口及 `scripts/universe_iteration/__init__.py`。A/B/C各自模块与同名测试/报告排他写入，不改共享runner/verifier。
- A：`lifecycle.py` / `tests/test_universe_iteration_lifecycle.py`；B：`actions.py` / `tests/test_universe_iteration_actions.py`；C：`capture.py` / `tests/test_universe_iteration_capture.py`。标准库优先，模块导入无副作用。各模块独立、不得互相import或import生产authority/Genesis；R单向组合三个模块，不循环依赖。
- R唯一修改共享runner/verifier及必要部署适配。模块的具体Python函数签名由owner在交付中记录并在R适配，不并行猜测共享调用。以下JSON字段及语义冻结，不能静默兼容变更。
- 所有文件写入exclusive、拒绝既存/符号链接；公共证据不读private owner/key内容。无新provision/信任锚/实机运行授权隐含在模块调用中。外部UI仅CUA；模块不能自行按键、截图或quit。

## 公共绑定与证据

ready后B/C使用的`binding`精确字段：`run_id, session, world_id, authority_root, source_sha, host_pid, worker_pid, generation`。

- session为initialize或existing；source_sha为准确40位小写SHA；pid/generation正整数（bool不算整数）；run/world为已批准卡标识；authority_root为canonical绝对路径。
- 每个validator必须接收独立的expected_binding并逐项比对，不能只把同一份自述与自身比较。PID实际启动身份另由A提供，日志/trace需R关联验证。`trusted_head`与`selected_observation`分开，history所选(0,1,1)不改变可信current(1,2,2)。各自为精确非负整数 `tick,revision,watermark` 三元组，与已验证observation/manifest关联；不得把任意label当验证后观察。
- 公开文件引用统一 `{path,sha256}`；路径绝对、无symlink，摘要验证实际原件。map保持既有authority_map `{root,files}` 格式；逐动作before/after比较完整files，不限HEAD。细节raw只留独占DevSSD目录，仓库报告引用摘要。
- 时间使用同一controller单调时钟域并记录UTC anchor/时钟域标识；跨进程/UE时钟仅经独立锚定转换，不直接相减。捕获区间不用伪精确单点。
- 模块验证成功只表示结构及已提供证据一致；真实UI效果/可信bootstrap/原件来源仍需独立review，禁止直接授G-B2。

## A：生命周期及资源

数据版本 `universe-i13-lifecycle.v1`；进程身份记录 `pid, ppid, start, argv`（start为ps启动身份原文，argv完整原文），观察时间同时记录monotonic和UTC。实际已接受UE路径/bundle匹配由外层固定，不由任意输入选择命令。保存每次被动进程清单原件；观察覆盖launcher后代与同bundle脱离实例，独立于supervisor存活。

A提供：纯预算决策（UI许可/quit_due/stop及理由），被动CLI进程观察接口，进程身份匹配，时间区间并集核账，全局账本验证。只允许固定ps查询，无UI、无自动launch、无不归属进程kill。若需要清理仅沿用runner既有精确owned清理/父wait，A不另造全局kill路径。

- 新实机卡dispatcher启动全局时钟，至launcher实际wait、全部本次进程静默、controller observer结束及最后封存结束。所有attempt完整保留。旧I12独立2566/1200 fail不重置。
- 每session420s：build60/startup60/interaction240/normal shutdown40/seal+observer20；最迟session360s quit、400s父wait+回收、420s完成该会话封存。阶段超限提前quit；最后60s不能继续动作。global1200s/2GiB仅待R冻结的提案；最终封存180s、异常收束/保守差额180s不授权第三次会话或重试。
- 检查返回stop/quit_due时，B只能释放输入并走正常quit，不继续采证；最迟quit前每次CUA操作/tool等待上限10s，且不得超过当前剩余动作余量；正常quit由唯一CUA owner执行。guard不产生“已退出”证据。
- 全局账本含dispatch/end、session/stage时间、完整observer样本/间隔、实例identity和起止区间/归属、wait证据、未知/污染、封存时点及whole-storage bytes。间隔/未知边界保守计费，观测缺口不pass；未知exit不写0，ps消失不证明正常退出。
- 同期未知归属UE视为contamination，拒绝新UI/开窗，记录保守上界并核实，不直接杀用户进程。阶段/会话墙钟和进程时间分别计量；并行实例时间取区间并集不重复计，非重叠额外实例补入。

### A固定账本shape与判定单位

时间字段均为同clock域的有限秒数（非bool），UTC为带时区ISO字符串。`run_binding`仅 `run_id,source_sha,world_id,authority_root`，预启动无PID；session进入ready后才要求完整B/C binding。未知PID仅build/startup可为null，不能获得UI ready/normal许可。全局ledger不强塞某一session的完整binding。

```json
{
  "format": "universe-i13-lifecycle.v1",
  "run_binding": {"run_id":"...","source_sha":"SHA40","world_id":"...","authority_root":"ABS"},
  "clock": {"id":"controller-clock-unique", "anchor_monotonic":0, "anchor_utc":"ISO"},
  "dispatch_monotonic":0, "end_monotonic":1200, "limit_seconds":1200,
  "max_observer_gap_seconds":2,
  "samples": [{"monotonic":0,"utc":"ISO","processes":[{"pid":1,"ppid":0,"start":"ps start","argv":"exact"}],"raw_ref":{"path":"ABS","sha256":"SHA64"}}],
  "sessions": [{"session":"initialize","start_monotonic":0,"end_monotonic":420,"binding":null,
    "stages":[{"stage":"build","start_monotonic":0,"end_monotonic":60,"deadline_monotonic":60}],
    "completion_ref":{"path":"ABS","sha256":"SHA64"}}],
  "processes": [{"identity":{"pid":1,"ppid":0,"start":"ps start","argv":"exact"},"ownership":"owned",
    "first_seen_monotonic":0,"last_seen_monotonic":1,"start_lower_bound":0,"end_upper_bound":2,
    "boundary_source":"observer-bracket", "wait_ref":null}],
  "seal":{"started_monotonic":1180,"ended_monotonic":1200,"observer_ended_monotonic":1190,
    "storage_bytes":0,"storage_limit_bytes":2147483648,"storage_snapshot_ref":{"path":"ABS","sha256":"SHA64"}}
}
```

此shape为结构示例，数值不代表已观测结果。ownership枚举owned/contamination/unresolved；boundary_source枚举parent-wait/observer-bracket/conservative-upper-bound。阶段枚举build/startup/interaction/shutdown/seal；session可暂缺（仅全局已开始尚未launch），存在的实际session必须最终有五阶段、完整绑定及真实completion才满足两会话门。阶段允许提前结束，deadline不得晚于session上限及固定阶段预算。

observer目标周期0.5s、最大相邻样本间隔2s（包含dispatch到首样本与末样本到observer结束边界）；大于2s为观测不完整/inconclusive，未知归属为污染fail，不能插值冒充正常连续观测。最后样本必须无本轮存活进程；原始CLI样本引用须可复算。正常wait_ref指向实际父wait收据，不接受ps缺席替代。

硬门使用连续`end_monotonic-dispatch_monotonic≤1200`，最终封存结束=end，observer结束≤end；进程区间union单独报告，用于保守核对遗漏，绝不代替更大的连续墙钟。seal storage_snapshot覆盖所有本轮存储（不读key），未知/缺字段分别返回fail或inconclusive，不能用covers_all_attempts布尔宣称pass。A实现可增加明确诊断字段，但不能删除以上必需证据或放宽阈值。

## B：逐动作manifest与收据

版本 `universe-i13-actions.v1`，生成固定有序manifest。每项：唯一 `action_id, session, kind, commands, max_seconds, phase, charged_budget, trusted_head, selected_observation, expected_operations, required_evidence`；commands是审定CUA操作说明，不可由模块shell执行。收据必须绑定binding/action、before/完成事件/after/restore原件、log dev/inode/prefix hash/before offset/after offset，trace范围及预期请求响应，开始/完成时间，实际效果独立读回。缺after/陈旧marker/错world/PID/head/不完整释放与恢复均拒绝。不能只靠提交receipt宣称发生；R要关联真实日志/trace/图片及独立review。

沿用runner PLAN，**S1**：bootstrap/init(0,0) → retain(0,1) → weak physical(1,2) → retry → exact history(0,1)/(0,0)/current(1,2) → history_write_rejected → held_input → camera → visibility → framerate → pause → exit1；两Native测试 ProtocolIds/StandaloneAssetAudit精确执行且Success。**S2**：仅existing，fresh status+自动observe current(1,2)，explicit current(1,2)/history(0,1)/restore current(1,2)，exit2；无initialize/prepare/advance。

- S1初段先原PNG/quit guard检查，失败立刻退出，不另开probe会话。S2前置S1同card/source normal完成，不能用repair-only替代。
- retry确为新的request ID、原command_records/digest相同的advance，再status/observe；不得新prepare/扣预算。history为真实observe请求及匹配响应，不以目录代替。
- history Space、R都拒写，trace无prepare/advance；held Space从history按下，保持跨回current，再释放并读回；不能在current首次按下引发推进。每个子动作都有完整map、实际完成读回及恢复，不用批次首尾替代。
- camera变换和恢复、visibility false/true、t.MaxFPS改变/readback/复原、pause/resume实际readback都必需。当前UE缺部分完成marker，输入工具可能缺跨call持键能力：这属于R必须解决或no-go的缺口，不能用自述补齐。若需UE新增只读诊断marker，R提出独立窄任务/接口版本，不能在B越界修改产品。
- manifest输出逐命令+marker+map+PNG/必要图片+恢复的上限之和，仅interaction项S1≤240s/S2≤240s；每项phase/charged_budget显式startup、interaction或shutdown，bootstrap/init/exit不能暗漏计；上限为提案，不是实测。R逐项核对实际可执行能力和耗时依据，缺证则no-go。预期业务请求数固定S1=20（init4、retain4、physical4、retry3、history3、拒写前history1、held回current1）、S2=5（status/autoobserve及显式三observe），每类请求响应具体字段由B输出schema并由root复核；readonly_pairs明确覆盖camera/visibility/framerate/pause/history/history_write_rejected/held_input/retry/revisit九类。owner依据源码逐项列出，额外请求需解释，禁止只检查“至少存在”。

## C：原生PNG与捕获区间

版本 `universe-i13-capture.v1`。两步被动接口：prepare_native_shot绑定expected_binding、head、已验证observation引用、log offset及期望WxH/SDR、新目标路径的父dev/inode和原文件不存在；返回唯一CUA命令 `Shot filename="ABS.png" nosuffix`（如需HUD显式showui，契约清楚区分）。collect/verify核验同prepare、实际CUA命令receipt与时间、稳定新文件、before/after maps及实际expected_binding。

- 请求须在verified observation后，stable文件完成≤实际before_exit，报告request→stable区间，mtime/processed delegate不是拍摄时刻或成功证明。真实Shot与Metal/viewport/HUD的绑定仍需独立review，不由路径命名推断。
- 不使用startup ExecCmds/HighResShot、外部截图或JPEG转码。保留真实原字节；HDR可能生成EXR，按magic拒绝；命令accepted/processed广播也可能没有写成功，必须实际新文件通过验证。
- 检查PNG signature、IHDR/WxH/可接受SDR格式、所有chunk边界/CRC、有界zlib EOF及解码scanline/filter、IEND且无尾随字节；限制解压量和总字节。拒绝损坏/伪装/陈旧/路径重定向/inode替换/覆盖/错绑定/缺时间区间。

## R：兼容与开窗门

I13不向旧 `universe-i12-r12.v1` 静默加入新stage语义。R负责新 `universe-i13-r13.v1` 外层卡/账本及证据版本适配；保留旧runner/verifier严格行为。复用旧监督器时可使用内部兼容卡，但必须明确两卡hash/所有字段映射，新层退出/seal/global ledger优先且不可绕过；没有完整适配就no-go，不按旧subtotal冒称新资源通过。

新证据 `universe-i13-evidence.v1` 引用旧结构bundle并额外强制A全局账、B逐动作、C原PNG区间、S1/S2正常completion和独立review。不得将时间区间伪装为旧captured_at单点；旧bundle所需旧字段只用真实已知观测，不捏造精确拍摄时刻。兼容无法诚实表达则新版分支独立验证，不修改旧证据。

R离线ready不等于PNG/正常退出已实测。新卡必须固定最终产品/tool source、二进制/pins、world/root/anchor、私密owner输入依赖与bytes总量、逐动作manifest和全局预算；只在ready后统筹明确dispatch实机卡。缺真实读回、持键能力、240s可行性或版本适配任一项，no-go并由V结算，禁止悄悄降门/追加试跑。V always-run：失败/中止也结算；下游skipped，残留保持开窗禁令。
