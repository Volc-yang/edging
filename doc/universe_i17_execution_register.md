# I17：Mac Native 完整四项验证

2026-11-07；**partial，已独立结算**。输入0965d97；[方案及v2](design/universe-i17-native-completion-plan.md)。真实四完整测试全部Success、三个旧proof全部接受，但后验TraceServer晚写使原console/完整静默门失败；Trace纠正已审查/CI/集成，第二次没有dispatch。root唯一运行owner，无UE源码/physics/C++改动，旧失败不覆。

| 节点 | owner / 固定输入 | 状态 / Check |
| --- | --- | --- |
| 0 | root，i17_review独立审查 | 方案及短路径/v2裁决接受；最多两窗口/每卡单次/180s/2GiB，v1墙钟900→显式v2总1200、每次≥270s预留，不重置起点 |
| C | i17_controller；`.worktrees/i17-native-completion`，初分支`codex/i17-native-completion`，最终`codex/i17-native-no-trace-server` | PR123/218504d→cd6d1c6，CI42369719523 success；N独立9新+18旧CPU通过。无$前缀/23项inventory、97字符独占DDC、writer barrier与seal复验已交付 |
| C纠正 | 同C | PR124/58fcab7→6d184d8，CI42371060080 success；N独立affected2CPU通过。两个真实Trace关闭参数+exact sponsor归属；root029defe合并代码与本地v2文档。代码接受但未实机复测 |
| P/R | root准备，N ready审查 | complete准备；复用准确build/native5a6cca0，实际tool cd6d1c6；新prepared1aee6c9f/card3d856a9c/manifest56a2a4f6和完整source/binary SHA独立ready通过。所有初次实现/CI/准备在首clock前完成 |
| T1 / T2 | root | T1 partial：UE51581/parent51564，真实wait0；四Success/case3成功；后验console/actor完整性fail。T2 skipped：虽纠正CI通过，v2也不足270s完整预留，未创建第二卡/manifest/UE；只保留空attempt2/prep目录 |
| A | i17_review，root结算 | complete独立停止路径审查；原报告commit776b217等价review集成，见[I17A](evidence/universe-I17A/report.md)。不创建pass Native review/policy/coverage，不以四测试成功掩盖console/完整监督/预算失败 |

原output_root仍为`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe`，本轮原件目录`I17-20261107-native-completion/`；DDC实际`ddc-i17-9a684908890ee50a`同root下97字符/Isolated Writable、无Zen启动。所有继承/新增root字节一并计量；五候选外域before/after为metadata-only，root源/binary/owner/context/inputs/keys不重建不迁移，61-file authority前后map一致。

## 当前权限与发布事实

本轮sandbox限制写workspace、DevSSD写/ps/联网需正式升级。独占DevSSD mkdir及metadata baseline/ps已分别获自动审批允许。第一次git push升级被拒，理由remote ownership/trust和payload发布授权未建立；没有改用其它渠道绕过。随后GitHub只读连接get_user_login返回Volc-yang/56686828，owner列表确认同用户拥有公开Volc-yang/edging/1291093087、admin/push true且origin匹配；附此新增证据重提同一git push获批准，f8d4822/61a05b1已成功推送。后续权限仍按具体操作审查，不把此次批准当无限授权。

用户主checkout、I12B恢复树与既有构建树保留；旧blocked goal状态不改。未安排网站/DNS/API、crash report发送或UE引擎源码修改。

## 首卡实际与v2裁决（第二卡前持久记录）

PR123/218504d经N独立9+18 CPU及CI42369719523 success，merge/tool cd6d1c6。真实首UE51581/parent51564、parentwait0，四完整测试Success、case3接受；controller43.195s/outer43.561s。DDC实际Isolated短路径Writable、无Zen启动、barrier报告complete。但后验console1815→2665B，旧SHA只匹配明确derived prefix：TraceServer52541 ppid1且--sponsor=51581，原parent-chain-only quiet漏报；首原resource/receipt不可覆盖，first-attempt-postseal-review ca38244a保留。61-file map不变；五已知外域UBT3项rotation/656B，新增Trace域当前13files/11790B须加入完整账。

唯一纠正58fcab7的两个真实Trace关闭参数与exact sponsor归属经N独立审查/affected2CPU，CI42371060080 success后集成。原900s的270s完整预留已不足，v1门不称通过；按root提议/N明确接受的方案v2，本轮整体首dispatch连续wall上限只增加至1200s(+300)，不重置起点、不加两次窗口/每次180s或2GiB、不再延期。第二独立卡沿用旧900政策，最终同时报告两卡整体v1/v2账与第二有限门；不得用第二结果补第一console/observer缺口。

## 最终实际门与资源

- **实际通过事实：**Found4、IdentityAndDefaultOff/HandledInputAndOrder/PauseReadWithoutTick/PublicProofReplay四完整Path各Success；case_count3/acceptedtrue/error空。原status信任链/五输入SHA/Manifest-State-Event及selected31/42/45记录由独立review核算。只有一次Native，未新solve/history/retry，不安排Metal。
- **封存后验fail：**原controller的normaltrue/quiettrue/barrier complete原件保留，但TraceServer52541实际`--sponsor=51581`、ppid1逃过父子链归属；console1815→2665B，原SHA失配。明确derived prefix1815B与原SHA一致，只作派生恢复，不冒称原路径仍不可变。原首卡整体Native review不能pass。
- **监督与字节：**controller活跃段持续ps，Trace晚写暴露完整actor覆盖缺口，不把修复间隔补作连续pass。已知五外域仅UBT3项rotation/656B变化，全局DDC/Zen无新增；Trace域缺首前baseline，当前整域13files/11790B保守计量并保留归属限制。最终自有UE/Trace均静默，未发送清理信号。
- **最终wall fail：**`prep/final-campaign.json` SHA `aebdbca55cd459ff204e263ce548a992597e690b13a38806de13230de95eac6b`，首outer→实际最终封存 **1206.800294s**，v1>900、v2>1200均不标通过。最后封存权限调用前已不足270s，故未派第二；审批/复盘尾部约6.8s超v2也照实保留，不以43s controller subtotal代替。完整root+whole Trace+已知外部changed files+余量保守 **1,558,560,201B<2GiB**，该测量不抹去首Trace覆盖缺口。

[330项当前原件及DDC索引](evidence/universe-I17R/runtime-evidence-index.json)同时保存原receipt/current console/明确派生prefix/外域metadata，不含owner原文/key内容。首UE启动原Dataflow Date错误继续保留，未改引擎源码。后续报告/清理见R/A。

## 下一轮唯一入口与排期复盘

本轮Trace纠正已经代码审查和最终CI通过，**下一轮不再排工具实现/CI研究，直接冻结最新工具源的新prepared/card/manifest后，一次实测已合入的NoTrace+独占DDC+无$四项组合**。复用5a6cca0二进制并逐字节复核，不无理由build。新的运行卡必须在全部离线准备/权限/ready完成后开始clock，旧卡、旧预算失败与所有原件保持；本轮没有通过新周期重置继续运行。root对修复/审批/CI耗时的预留不足负责，下一轮将工程准备与实际运行阶段清晰分开。

G-B2/完整Metal输入PNG/标准双会话仍开放；没有formal Native pass或旧语义gap解除。构建/恢复树与全部DevSSD原件保留。两个任务树在A报告集成、干净/提交保存/公共运行依赖核对后non-force清理，分支全部保留，见[R结算](evidence/universe-I17R/report.md)与[清理记录](evidence/universe-I17R/worktree-cleanup.json)。用户主checkout/旧blocked goal/网站DNS/API/crash report发送均未改。
