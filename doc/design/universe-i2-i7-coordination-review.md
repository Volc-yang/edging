# I2 / I7 独立交付与统筹接受（2026-11-01）

## I2 所有权

PR #79，source `232e0a74a2d5de48fd8bb8529f0c9149877db8b2`（普通合入I1 prerequisite `efba6fa`），merge `d2b7d29d8602db7da8f19bf21637fce98123dc36`。仅ownership.py及专属测试；主统筹静态复核稳定fd锁、根/注册/lock inode、no-follow/nlink1、fork close不LOCK_UN父锁、纯读零创建和错误/fd释放边界，接受本卡。

首轮24tests通过但**未保存磁盘raw**，只有原工具输出，临时目录按测试设计已清理；不追补声称为原件。动用本卡唯一剩余定向重跑，准确不变head，新attempt2 24tests通过/exit0/runner0.268秒；3.10语法通过、输入前后hash不变。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I2-20261101-independent-record-attempt2/raw-index.json`，SHA `f7a8f9d1781b5be25b1cd06404479771e3a2926782cd2815280824fc5600ef46`，root独立复算8/8文件size/hash通过。它是新run单元测试日志，不是首轮原件，也不替代I6完整文件图/PID故障轨迹；无第三次运行。

最终head CI verify success（run41319032348/job124885108820）。预期head合并后确认source祖先且干净，移除 `.worktrees/i2-universe-ownership`，分支/证据保留。I2 complete；G-S1仍planned。

## I7 静态物理契约

PR #80，source `e005c2c3d00dd97cf0f811550545b19fa249992c`，merge `fe2176a1fd24309c03bcf1542ede0029ee041810`。仅9个contract/fixture文件；1动态Sphere+1固定Box。Owner一次stdlib静态Check通过：11个精确double差D向量+4个已缩放half-even向量、9安装源码/METADATA hash、fixture未变，未import Genesis。

非作者u7独立递归canonical复算config固定字节/v0.2前缀hash，Fraction整数商余复算11+4向量；只读源码hash/AST/getter/contact语义一致。root读精确契约及源9/9size/hash复算接受 **G-P0静态技术门pass**。最终CI verify success（run41319193490/job124885588223）。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I7-20261101-static-attempt1/`：final-source-index SHA `01036efcc5f2845d57beb696a93594e5da95ebb125eecc792ff9a814593683b8`，stdout SHA `493ffe1b5a5556ea59dcd5f5659a50e6547e95c692d61c45cca4797ab5d677a6`。干净且source为集成祖先后移除 `.worktrees/i7-universe-physics-contract`，分支/原件保留。

I7本卡complete；v0.2 schema/API/raw profile仍提案。G-C0.2必须补有界Observe proof bundle、U5六区typed起源/路线水系/存在/投影及完整计数、provider/default/build身份关联、同tick异revision实验机制；I8/I9/I10前暂停这些受影响共享接线，G-P1/G-B0均未接受。

## 父级集成Check与Act

准确集成 `d2b7d29` 上单次运行现有两套suite：39tests/0.300秒/exit0，source+fixture输入hash不变。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I1I2-20261101-parent-integration-attempt1/index.json`，SHA `2ec73ce10a98f7fe7752913b840c794c69a34419a99480b153a7d631f9664a25`；仅统筹文档dirty，运行源码为该提交。

I3依赖已满足，继续v0.1存储事务；I0E按原U9“共享契约差距重开I0”规则新增局部契约卡（已由统筹审阅此差距/边界并派发），独占新v0.2文档/fixtures/oracle，先给方案裁决后实施固定契约；不修改旧档或未受影响内核。I0E最终非作者字节/引用/计数Check才可冻结G-C0.2，受影响模块另派局部卡与故障复验，不用文档合并跳过实现。
