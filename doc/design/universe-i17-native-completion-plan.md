# I17：修复 Mac Native 调度与缓存/封存边界

2026-11-07；用户“继续”授权执行 I16 Act；输入0965d97。root方案：完成实际四精确测试、三旧proof、正常wait/后代静默/稳定原件的独立验收。仅插件工具/启动配置，UE发布版和5a6cca0既有构建优先；不改引擎/physics/C++，不安排Metal或新solve，不授G-B2。

DAG：0独立方案审查 → C启动/缓存/封存窄修 → 独立代码review/CPU/PR/CI → P新原件准备与独立ready → T真实Native → A独立验收/上下文commit/清理。root唯一运行owner；reviewer不启动UE/build/worker，不读owner/key。准备/CI在第一次dispatch之前完成。

C排他capability.py/对应CPU tests/evidence I17C：四完整selector用无`$`的`^`前缀，离线冻结已编译项目测试名称inventory并证明四前缀唯一；运行仍严格Found4、四完整Path集合和Success，不放宽验收。Native argv加仅指本次新目录的FileSystem DDC图及真实-DDC-NoDefaultGraph，核实际graph/path日志，不猜NoZen参数。等待真实父wait后，在phase剩余额内等待连续新样本证实全部已观察owned后代/extraUE静默；仍活着则失败，不强制结束当normal。只在写者退出、console稳定后生成最终不可变引用，seal再次验证稳定；不覆盖旧receipt，不重建原I16console。

C只读发现/root裁决、N独立接受：安装版FileSystemCacheStore.cpp70–78/3068对Mac缓存根限制119字符，长evidence目录下ddc会超限。DDC固定为`prepared.output_root/ddc-i17-<run_id与controller_output绑定SHA256前16位>`，独占真实创建，长度<119、无symlink或图解析标点，全部纳入原output_root字节；evidence/controller仍用本轮独占子目录。同run不同纠正attempt不碰撞，不改变36字段/API或重用旧缓存。

P/root：沿用原I15 output_root并全量计量（约1.5GB），本轮独占I17-20261107-native-completion子目录，新run/tool/prepared/card/manifest/provenance；product/native/binaries源5a6cca0及owner/context/inputs保持，所有实际source/binary/authority map再核对。外部已知写域记录baseline/after元数据；若仍有未计量外部写入，资源覆盖保持inconclusive而非冒称通过。写DevSSD/启动已安装UE需按当前sandbox权限申请必要执行权限，自动审查拒绝时保留原因，不绕过。

T/root：每卡只一次Native，180s phase、global900s/2GiB沿用。整个本轮运行campaign从首dispatch连续计账不重置；首次正常只一窗口。若仅启动配置/采证缺陷且未改变权威，可在明确root纠正及新source/新卡/独占新attempt后最多再一个窗口；原失败保留，剩余≥270s才派发，总共不超过两次/900s，不进行无限自动重试。第二次仍不通过则结算最小缺口，产品断言失败不靠重跑掩盖。

A：独立实际Found4/四Success/case3输入输出精确hash/strict parser/actual parentwait/observer≤2s/全部后代及写者退出/原console封存后不变/authority map不变/完整预算。原UE Dataflow启动错误保留；有新事实再诊断，不因此改引擎。正式Native review只有全部所需条件通过才产生，三旧响应之外无语义授权；I16/I15/I12失败不覆盖。文档提交/任务清理依仓库工作流，用户主checkout及恢复树不碰。

## I17 v2：唯一条件纠正与显式 wall 预算修订

首卡实际四Success/case3/parentwait0，但独立后验发现console晚写：UnrealTraceServer双重fork、ppid1，实际`--sponsor=51581`归本轮，原parent-chain quiet漏归属。首卡原resource/console引用不覆盖，记录为后验失败。C最小纠正58fcab7添加安装版TraceAuxiliary.cpp2365/2378真实支持的`-notraceserver`、`-traceautostart=0`，并从唯一exact sponsor与TraceServer首token识别已明确本轮归属，不杀unknown/其它sponsor；另加Trace元数据候选域。N独立review和受影响CPU接受，CI最终成功后才第二卡。

root提议/N独立接受：原整体900s预留不足主要来自离线修复/审批/CI，v1原预留门未满足事实保留。仅把**本轮首dispatch到最终seal wall上限改为1200s(+300)**，不重置起点；两UE总次数、每次180s、2GiB及每卡原900策略均不变。第二必须按v2剩余≥270s、仅一次新source/card/attempt，绝无第三窗口或再延期。最终分别报告v1/v2预算结果，不能用第二subtotal遮旧账或把1200合计塞进旧900 verifier。第二独立卡完整observer/normal/immutable/exact3可单列验收；第一gap/console失败及全campaign不连续监测不能倒填成pass。这是内部资源模型的版本化调整，不是隐藏旧失败。
