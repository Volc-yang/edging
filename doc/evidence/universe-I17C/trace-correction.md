# I17 条件纠正：TraceServer sponsor 与禁止自动启动

首次I17真实Native已由root执行：四测试/三case成功，UE wait0，但parent-chain观察未归属一直ppid1的`../../../Engine/Binaries/Mac/UnrealTraceServer fork --sponsor=51581`，原console在seal后追加，原失败不覆盖。本修正仅追加已安装TraceAuxiliary.cpp2365–2368/2378支持的`-notraceserver`和`-traceautostart=0`，不修改engine或Native源码。

归属补充只接受真实首token basename UnrealTraceServer及唯一完整`--sponsor=<phasepid>`，相关进程必须未出现在该phase启动前baseline；其它sponsor、子串、重复token、其它可执行文件均不归属。既有静默/稳定barrier会拒仍活着的自有sponsored actor，不以unknown进程作为kill目标。本任务未运行UE/build或改DevSSD/private状态。

实际定向CPU两项通过：真实raw argv形态的ppid1 sponsor归属/错误sponsor与预存身份拒绝，以及Native实际构造argv两个关闭flag。新回归通过既有CI发现入口运行。旧测试与完整真实四test/退出/封存验收不放宽；需独立review、最终CI和root在共同900s余量内第二张新卡实测。测试2项0.013s；`git diff --check`通过。
