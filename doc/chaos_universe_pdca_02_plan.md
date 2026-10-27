# PDCA-CHAOS-02：呈现可测性与六类场所复核

基线：`7cb65d2`（第一轮迭代集成结果）。统筹分支：`codex/chaos-pdca-02`。第一轮 C2 报告 `doc/evidence/chaos-pdca-01/visual-review.md` 是本轮问题清单；不进入 TWO 演化。

## 方案树

```text
PDCA-CHAOS-02 关闭第一轮未通过的呈现阶段门
├── H1 UE 可自动驱动的呈现检查入口 [实现，独立 PR]
├── V1 六类场所与路线的可辨认代理 [实现，与 H1 并行，独立 PR]
├── C3 Metal RHI 独立复核 [审查，依赖 H1+V1，独立 PR]
├── V1R 地形遮挡修复 [返工，依赖 C3 失败证据，独立 PR]
├── C4 遮挡修复后独立画面复测 [审查，依赖 V1R，独立 PR]
└── A2 主任务审查、集成、复盘与下一轮裁决 [依赖 C3+C4]
```

H1 与 V1 使用不重叠源码路径。共享输入为 P0 契约和固定 seed7 初态；改动共享接口须先由统筹任务裁决。主工作区用户改动、Seed→Tree PIE 工作树和状态目录不得触碰。优先使用 UE 5.8.3 发布版 API；没有可复现契约缺口不改 UE 引擎源码。

## H1：UE 呈现检查入口

- **目标：**提供不依赖人工按键的固定镜头、帧率、UE Pause/Resume、世界之灵显隐与 tick 0/1 Observe 控制；每项操作必须可从日志或机器可读证据确认实际发生。控制入口本身不得隐式 Advance；O1 仍须显式且只执行一次。
- **所有权：**新建 `ChaosValidation*` 命名 UE Host 源码/fixture，可在必要时对 `ChaosObservationGameMode.*` 做最小受控扩展；不得修改 `ChaosWorldActor.*`、Python Worker、树/Genesis 路径。
- **步骤：**先确定发布版 UE 的可自动调用入口；实现固定场景操作及可追溯日志；以 NullRHI/fixture 验证操作顺序与无隐式 Advance；构建 Editor/Game。若可行，真实 Metal 下执行最小控制探针。
- **验收：**固定命令能逐项确认相机变更、帧率变更、UE 游戏暂停/恢复、显隐及历史观察；失败或未执行不得写成通过。保留旧 Space/0/1 行为；初态和状态目录隔离。
- **风险：**UE 控制台在上一轮未可靠开启，不能仅凭发送按键声称已执行命令；可使用自动化测试框架或专用受限控制入口。不要使测试入口成为生产时自动推进权威状态的后门。

## V1：六类场所代理可辨认与路线

- **目标：**在固定 seed7 场景中使 city、wildland、plain、forest、river_marsh、ocean 和连接路线能逐区辨认，并给出固定镜头/观察点清单。只提高实验视觉代理可辨认性，不声称“近乎完美”的最终资产质量。
- **所有权：**`ChaosWorldActor.*` 与新的专用静态场景说明/fixture；不得修改 `ChaosObservationGameMode.*`、JSONL client、Python Worker 或初态数据契约。
- **步骤：**审查现有 place 坐标和遮挡；使用 UE 发布版形体、材质/颜色、光照及相机布局明确六类区和路线；以固定 JSON fixture 做 NullRHI 构造检查，记录各区镜头目标；将真实画面留待 C3 独立核查。
- **验收：**六类 place 与路线在构造/日志中有稳定 ID/坐标；真实 Metal 的逐区截图能独立辨别各类场所及连接，若仍不清晰则 C3 保留未通过。不得修改初态 canonical hash、O1 因果或权威存储。
- **风险：**BasicShapes 只能提供代理质量；视觉美术目标需另立资产与性能预算，不能以本任务冒充完成。

## C3：独立 Metal 阶段门

- **目标：**在单 UE + 单 Worker、隔离状态目录下，复核 CHAOS/ONE 及 H1/V1 的完整矩阵。
- **所有权：**只写 `doc/evidence/chaos-pdca-02/visual-control-review.md` 和小型证据索引；原始大图/日志放独立 Saved 目录并记录 SHA。缺陷退还对应实现 agent。
- **步骤：**固定只读 seed7 输入并记录 raw/canonical SHA；真实 Metal 启动，采两个状态；逐项执行相机、帧率、UE Pause/Resume、重复 Observe、显隐和一次 O1，逐项记录操作执行证据及前后 manifest/state/event/head；逐区截图核查六类场所与路线。
- **验收：**每项必须可复查地证明命令实际执行且权威摘要不变（O1 除外）；截图与 world/tick/watermark/log 绑定。未执行、白屏、仅 NullRHI 或无法辨认均标未通过。报告区分技术只读、场所连贯与最终美术质量。
- **风险：**D3/D4 对初态双次读取竞态仍在，运行固定只读输入并保留风险；macOS canonical hash 实现不代表跨平台通过。

## A2：统筹裁决

逐 PR 审查精确提交与 CI/本机检查，集成后核对 C3 结果；更新 `doc/parallel_execution_backlog.md` 和任务登记并提交。只按证据关闭阶段门；未通过项给下一轮明确入口。暂不将本轮直接合并到用户有未提交改动的 `feature/edge-world`。

## C3 反馈引发的返工分支（2026-10-27）

C3 真实 Metal 截图显示大块地形遮挡森林、河泽、海洋及路线。C3 保留原始失败报告，不修改实现。V1R 由 V1 原 owner 在独立 worktree 仅修复 `ChaosWorldActor.*` 的地形与 place/route 空间重叠，并更新镜头说明；不改初态数据、Worker、O1 或 H1。验收需构建与 NullRHI、固定 seed7 的 Metal 六区和路线截图。C4 从 V1R 集成提交独立复测受影响视觉门，逐图记录截图 hash、镜头坐标及 world/tick；既有 C3 控制/状态矩阵保持独立证据，不因视觉返工被抹去。若修复仍无法辨认，则保留视觉门未通过，不无限扩张本轮美术范围。
