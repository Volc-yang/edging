# I16：Native old3 执行登记

2026-11-03；**partial，已独立结算**；输入 d128053 / [审定方案53cd344](design/universe-i16-native-execution-plan.md)。实际一次 Native 接受全部三个旧 proof，但四测试/原退出静默/原console完整性门未过；G-B2继续开放。所有失败与实际成功事实分别保留，无重跑。

| 节点 | owner / 范围 | 当前事实 / 下一步 |
| --- | --- | --- |
| 0 | root / N独立审方案 | complete；明确Native-only，CUA已可用，不伪称不可用 |
| C | i15_controller；`.worktrees/i16-native-scope` / `codex/i16-native-scope` @53cd344 | complete；PR122 final5646124→merge4e7a58a，CI41568506690 success；N独立18 CPU通过，root审窄diff；没有Native代码变更 |
| P/R | root准备、N独立ready复核 | complete准备；保留产品5a6cca0与所有source/binary真实SHA匹配、Native源无diff，不重build；tool4e7a58a。新prepared27e4642f/cardb75a96d6/manifest5cb7e97a逐项独立核查；新clock前离线完成 |
| T | root唯一运行owner | partial；唯一UE PID64536，parent64525，actualwait0/25.245806s；outerwait0/26.601s。实际仅PublicProofReplay Success，三个case accepted；另三个测试未运行。原normalfalse/resourcefail保留 |
| A | N独立审实际原件，root结算 | complete独立结算；原docs commits1e21311+16a2c45等价review集成2b75a91+8acf973。未创建pass review policy/coverage授权，未解除旧语义gap常量 |

本轮独占输出 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe/I16-20261103-native-only/`。沿用原output_root，约1.47GB继承binary/scratch全量计量，位置/私密校验未放宽；新prepared仅run/tool/before_map_ref/created_at四项变化，provenance及原件保留。未读key内容、未改权威状态、未开worker/solver/Metal、未碰用户主checkout或I12B恢复树。

上轮I15的771s与observer失败仍独立保留，本轮不是重启上轮预算或覆盖失败。只运行新预算下已批准的单次Native节点；出错保留新原件并最窄结算。CUA当前可用但不因可用而追加可见窗口。

## 实际 Check

| 门 | 实际证据 | 判定 |
| --- | --- | --- |
| old3真实严格解析 | `(0,0)`31、`(0,1)`42、`(1,2)`45 selected records；case_count3/acceptedtrue/error空。N逐项核五输入SHA、原status信任链、请求ID/水位、Manifest/State/Event/selected digests；原桥调用既有strict parser | 仅这些旧响应实际接受；不是新solve/history或全门pass |
| 四精确tests | Found1、仅PublicProofReplay Success。实际argv含四个`^selector$`，安装版LaunchMac.cpp116–117把`$`替换为引号，ue.log403显示参数截断 | fail；其余IdentityAndDefaultOff/HandledInputAndOrder/PauseReadWithoutTick未执行 |
| parent wait / observer | UE parentwait0，无forced cleanup；49个实际ps样本原件哈希一致，最大gap0.564432s<2 | controller活跃段通过；不等于完整后代退出 |
| 退出静默 | seal时Zen64908从UE子进程转ppid1仍活着，原resource quietfalse/decisionfail，execution normalfalse | fail；cleanup-before时它已自行退出，actions=[]，未发信号，后续静默不改原门 |
| 原console | seal后原console从1802变2652B，原路径SHA不再匹配execution引用；当前前1802B恰好匹配原SHA，独占保存明确derived prefix和provenance | 原路径完整性fail，派生prefix不冒称原快照恢复 |
| 只读与资源 | 61-file before/after及独立fresh map一致；firstouter→最终边界353.430s<900。完整继承root保守1,496,872,753B<2GiB，新目录约25.36MB；Zen实际写域在外部共享cache且无pre-run baseline | map通过、本地root/time有界；全输出字节coverage inconclusive，不称整体资源通过 |

UE启动原日志1258/1260还记录engine DataflowNodes的Date未初始化错误：保留为未诊断启动风险，与随后case事件分开；不把它归因本插件或修改引擎源码。

独立报告：[I16A](evidence/universe-I16A/report.md)。[149项当前公开原件索引](evidence/universe-I16R/runtime-evidence-index.json)同时保留原receipt/current console/明确派生prefix；不含owner原文或key内容。campaign summary SHA27afbf00a0edb8b4f89957992735d0f7f12f65f15dbf86ad7d7a413a33a1005e，原resourcefail不覆盖。

## Act / 下一轮入口

不重造proof/physics/C++框架，不修改UE引擎源码；先离线做两个有直接证据的配置窄修并独立审查/CI，再新预算单次运行：

1. Mac避免`$`：四完整名保留`^`、去掉末`$`，冻结测试名称inventory证明每个前缀唯一，最终仍强制Found4和四完整Path/Success集合全等；不可把prefix本身叫作精确全等。备选唯一Automation group双边匹配也仍需inventory/实际集合核对；`StartsWith:`会补点，不用于完整叶名。证据为LaunchMac.cpp116–117、AutomationCommandline.cpp133–135/158–160/216–227。
2. 采用已文档化的独占filesystem DDC graph及`-DDC-NoDefaultGraph`防默认Zen回落，路径只指新DevSSD输出并核实际graph/path日志。候选`-DDC=(Isolated=(Type=FileSystem,Path=<run>/ddc,PromptIfMissing=false,Clean=false,DeleteUnused=false))`；依据BaseEngine.ini2753–2766/2851–2868与DerivedDataBackends.cpp695–720，不猜NoZen参数，不使用仍含Zen的NoShared/Cold。不能静态保证其它模块不启Zen，仍须全写域baseline/后代身份与所有写者退出后才封存console。

以上是C只读调查/Act提案，**尚未实现或实测**。新scope不得覆盖本次卡/失败，不用新结果倒填本轮未执行tests；Metal、标准双会话与G-B2仍开放。构建树/集成工具树/I12B和全部DevSSD原件保留。两个任务树已按最终干净/提交保存/公共运行配置无引用核对后non-force移除，全部分支保留：[R结算](evidence/universe-I16R/report.md)、[清理记录](evidence/universe-I16R/worktree-cleanup.json)。
