# 旧测试报告弹窗与报告器退出故障

用户截图：ULocalPlayer Within=Engine，却以 GameInstance 为 Outer；调用栈
指向 FEdgeWorldVisitorMovementTest::RunTest。旧 ensure 的 UE PID 为 52521，
属于 H6B 失败夹具。最终 `c3a00f8` 已改为 GEngine Outer，两项测试成功，
此前失败及原始报告均保留。此错误由测试代码引入。

无参数重启的 CrashReportClientEditor 多次自动选择同一旧报告。统筹确认
61164/61413/62297 的窗口与客户端日志均不对应新的 UE/Worker；不能把截图
当作新的游戏崩溃，也不能忽略它对用户及受控测试的干扰。

系统 ips 进一步证实报告器自身存在退出阶段故障：62236、62196、62131 等
为 SIGSEGV/EXC_BAD_ACCESS，主线程经 NSApplication terminate/exit、
LowLevelTasks::FScheduler::StopWorkers，再在日志输出设备中崩溃。
16:39 的正常窗口关闭虽然写出了 LogExit，仍不能据此判进程干净退出。
CoreServicesUIAgent 后续有启动请求；实际发起者尚未完全归因。getApp 可启动
不存在的应用，先前绑定与关闭后观察使来源判断混杂，不宣称唯一重启原因。

统筹保存报告/客户端日志/ips/截图后，只对精确匹配的残留 reporter 62297
执行硬停止以绕过其有问题的正常析构路径，并释放本会话的 UI app 绑定。
154 秒后的进程复核无 reporter。没有删除旧 ensure、没有修改新故障报告设置、
没有改 UE 源码；报告器自身退出 bug 仍开放，不能宣称根治。

独立原始目录：
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Reporter-52521-cleanup-20261101/raw/`。
19 份文件索引 SHA256：
`9f9a24f8013b5bbce9596592e7150c056488a1334ad0419ec4e85a84dd9e2842`。
包含坐标关闭未成功、早期匹配未发信号、最终精确清理与后续复核等记录；
只有实际过程成立的结果作为结论。不选择发送报告，不把应用自带分析通信
混写成“没有任何网络流量”。
