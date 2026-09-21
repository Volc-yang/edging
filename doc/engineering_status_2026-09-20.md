# Edge World 工程任务与进度分析

分析时间：2026-09-20
分析对象：`/Users/yangacan/edgeWorld/edge-world`（主工作区）+ `/Volumes/DevSSD/Unreal`、`/Volumes/DevSSD/Projects`（外置 SSD 引擎工作区）
数据来源：源码清点 + 实际执行测试/校验/构建产物核对，非文档转述。
扫描范围说明：第一版分析仅覆盖 `edgeWorld/`，遗漏外置 SSD 上的 UE5 工作区，已修正（见轨道 G/H 与 R9）。

> 结论摘要：项目实际主线已与 `EDGE_WORLD_PROGRESS.md`（2026-09-17，O3DE 路线）脱节。
> 当前真实形态是「Python 易经规则核心 + Chapter One 运行时 + Godot 游戏引擎实现 + SceneKit 诊断预览 + edging 64D/384 原型层」。
> 第一章以 Godot 为主实现，UE5 已建立读取同一快照的 C++ 对比基线；SceneKit 仍只是诊断预览。

---

## 一、实测证据（本次真实执行结果）

| 验证项 | 命令 | 结果 |
|---|---|---|
| Python 单元测试 | `.venv/bin/python -m unittest discover tests` | **83 tests OK**（0.23s） |
| 系统 Python 同测试 | `python3 -m unittest discover tests` | FAILED（1 error）— 系统 3.9.6 无 numpy，`cast_hexagram_batch_numpy` 抛 RuntimeError |
| edging 结构门禁 | `ruby bin/validate_spacetime_abstractions.rb --complete` | **structural validation: PASS / completion: COMPLETE** |
| 64/384/时空覆盖 | 同上 | hexagrams 64/64、line structures 384/384、canonical classical lines 384/384、confirmed scale anchors 2304/2304、八宫 64/64、游魂 64/64、归魂 64/64 |
| Chapter One 离线运行 | `python3 tools/run_chapter_one.py --offline` | 快照生成成功：schema **v2**，本卦 无妄 / 变卦 讼，chapter_score 0.9664，final_integrity 0.6724，decision_source=`rule_fallback` |
| 确定性评分器 | `ruby bin/deterministic_scorer.rb examples/sample-observation.v0.1.yaml` | 输出有效：validation_status=valid，top_families=乾(0.0188)/… |
| Swift 构建产物 | `preview3d/.build/out/Products/Debug/` | `EdgeWorldChapterOne`(956KB) 与 `EdgeWorldPreview3D`(733KB) 均已编译成功 |
| 第一章主实现引擎 | `/Applications/Godot.app` | **主实现平台**；`engine_platforms/godot` 读取共享快照 |
| SceneKit 诊断工具 | `preview3d/` | 用于快照检查和可视化，不计为第一章游戏引擎实现 |
| UE5 对比引擎 | UE 5.8.2 + `EdgeWorldUE` | Editor 目标编译成功；Commandlet 和 GameMode 均已读取第一章共享快照 |
| Godot↔UE5 合约 | `python3 tools/validate_godot_ue5_parity.py` | **match**：schema、8 灵、本卦、变卦、后天主灵、方位、洛书数一致 |
| Godot 第二处 | `/Volumes/DevSSD/Projects/EdgeWorldGodot` | 2026-09-17 的引擎验证骨架（20×20 地面 + 方块 + 相机，无脚本）；真实实现见轨道 C |
| O3DE 移除 | `ls O3DE EdgeWorld` | 目录确认已不存在，与进度文档一致 |

> **重要：外置 SSD 工作区**（上一版分析遗漏）
> `/Volumes/DevSSD/Unreal/` 是独立的 UE5 工作区（`Engines/`、`EngineSource/`、`Projects/`、`DerivedDataCache/`、`Tools/Scripts/`、`Templates/`），
> `/Volumes/DevSSD/Projects/EdgeWorldGodot` 是 Godot 验证骨架。二者均在 `edgeWorld/` 目录之外，**不在任何一份进度文档里**。

---

## 二、轨道清点（含规模）

| 轨道 | 路径 | 规模 | 职责 | 状态 |
|---|---|---|---|---|
| A. 世界引擎核心 | `engine/*.py` | 3903 行 / 11 模块 | 大衍筮法、64卦数学、分区世界生成、主观世界、编码可视化 | 可用，83 测试覆盖 |
| B. Chapter One 运行时 | `engine/chapter_one_runtime.py` | 523 行 | Ollama 限幅提案 + 规则校验 + 双阶段调用 + 确定性回退 | 端到端跑通 |
| C. Godot 引擎 + 诊断预览 | `engine_platforms/godot/`、`preview3d/`(SwiftUI+SceneKit) | 297 + 541 行 | Godot 承担游戏运行；SceneKit 只做快照诊断 | Godot 可运行，预览可构建 |
| D. Metal 客户端 | `edge-world Shared/Renderer.swift` | 702 行 | Perlin 噪声地形、网格、Metal 渲染管线 | 代码在位，ECS/相机漫游未做 |
| E. 原型评分层 | `edging/`(Ruby + YAML) | 1164 行 + 40 文档 | 64D 家族向量 / 384 爻位原型 / 320 相邻转移 / 确定性评分器 | **结构 100% 完成**，但与 A–D 无任何引用 |
| F. GTA V 源码 | `../GTAV` | 12 GB | 历史探索，已确认不可构建 | 阻塞且有损磁盘，属历史包袱 |
| G. **UE5 对比实现** | `/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` | C++ 解析器、Actor、GameMode、运行时 UMG、Commandlet | 与 Godot 对比验证共享快照 | 已编译并运行，玩家输入/Ollama/热重载闭环完成 |
| H. **Godot 验证骨架** | `/Volumes/DevSSD/Projects/EdgeWorldGodot`（外置 SSD） | 2 个文件 | 引擎连通性验证（地面+方块+相机） | 骨架，无脚本，已被轨道 C 取代 |

`engine/` 模块能力：`world_engine`（四象时钟、八卦地形规则、区域/瓦片、群系分类）、`dayan`（大衍筮法 + 批量/NumPy 加速路径 + 四象相位码 6→0/7→1/8→2/9→3）、`mathEdge`（64卦、八宫、游魂/归魂）、`subjective_world`（意识实体、易经仲裁、八原始卦灵、帝出乎震循环）、`live_cast`、`cast_visualization`/`cast_volume_3d`/`cast_argb_image`/`hexagram_image_codec`、`neural_network`（零依赖 MLP 基线 + 世界瓦片编码）。

---

## 三、任务完成度对照（按 `doc/edgeWorld_technical_development_plan.md` 与技术路线）

| 计划项 | 计划工期 | 实际状态 | 完成度 |
|---|---|---|---|
| 一阶段 1 项目基础架构 | 1–2 周 | SPM/Xcode 多目标结构存在，preview3d 双 target 已构建 | ~70% |
| 一阶段 2 程序化世界生成 | 3–4 周 | Python 侧完成分区域八卦地形+群系；Swift 侧 Perlin+Mesh 在位；Metal 绘制未端到端验证 | ~55% |
| 一阶段 3 四象时间系统与渲染管线 | 2–3 周 | `WorldClock`/`TimePhase`/四象相位码已完成；昼夜光照 Shader 未做 | ~45% |
| 一阶段 4 实体与交互原型(ECS+漫游) | 2–3 周 | **未开始**（`subjective_world` 是主观实体模型，不是渲染 ECS） | ~5% |
| 二阶段 服务端与"降神"玩法 | 8–10 周 | **未开始**（无 Vapor/Go、无 WebSocket、无 DB） | 0% |
| 三阶段 1 道生万物生命周期 | 4–6 周 | 阴阳/四象状态机已有基底（`phase_code`、`PrimalRunPhase`）；生态实体涌现未做 | ~30% |
| 三阶段 2 定数/变数系统 | 5–7 周 | 64D 行为向量与评分器**已完成本体**；"熵/变数触发"未实现，也未接入运行时 | ~50% |
| 四阶段 内容填充 | — | 未开始 | 0% |
| 五阶段 测试优化部署 | — | 83 单测 + 2 个 Ruby 门禁脚本；无 CI、无集成测试 | ~25% |
| **计划外新增：Chapter One「万物有灵」** | — | 运行时+规则校验+Godot 引擎+SceneKit 诊断预览+共享快照 v2 端到端可跑 | **~80%** |
| UE5 第一章对比实现 | — | C++ 八灵场景、运行时 UMG 玩家输入、异步 Ollama/规则回退、热重载、Commandlet 均通过 | **~55%（交互基线）** |
| **计划外新增：Godot 第一章引擎** | — | `chapter_one.gd` 读取共享快照，Godot 4.7 可打开可运行；另有 DevSSD 验证骨架 | **~75%** |
| edging 64D/384 原型种子目标 | — | 结构 100%（含 2304 时空锚点、原典 384/384 对应） | **结构 100%，产品 0%** |

---

## 四、缺口与风险（按严重度）

### R1｜进度文档失真（高）
`/Users/yangacan/edgeWorld/EDGE_WORLD_PROGRESS.md` 最后更新 2026-09-17，整篇是 O3DE 路线，而 O3DE 已移除、当前主线在文档中**完全不存在**。任何人（含未来的你/我）读该文档都会得到错误结论。

### R2｜四条轨道未接线（高·结构性）
已 grep 验证：`engine/`、`preview3d/`、`engine_platforms/` 中**没有任何一处**引用 `edging` 的 YAML 注册表或 `deterministic_scorer.rb`。即：
- edging 做完了 64D/384 原型与评分器，但世界运行时用的是另一套（`world_engine` 的八卦地形 + `chapter_one_runtime` 的规则层）；
- 两边连数据源都没打通：`engine/yijing_text.json` 原典数据**只有部分卦完整**（靠 `canonical_text_available` 标记），而 `edging/docs/02-domain-model/classical-line-texts.v0.1.yaml` 是 **384/384 完整**。

这是最大的返工风险：继续各做各的，将来合并成本会远大于现在打通。

### R3｜核心代码未提交（高·可丢失）
`git status` 显示 14 项未提交，且都是当前主力资产：

```
1042 engine/subjective_world.py          523 engine/chapter_one_runtime.py
 370 tests/test_subjective_world.py      131 tests/test_chapter_one_runtime.py
1270 models/chapter_one_snapshot.json    302 doc/subjective_world_chapter_validation.md
 541 preview3d/Sources/EdgeWorldChapterOne/  297 engine_platforms/
  38 doc/chapter_one_cosmology.md         56 tools/run_chapter_one.py
```
分支 `feature/edge-world` 已推送但停在 `de2794b`，本地工作全在工作树里，**无 git 历史保护**。

### R4｜测试环境不统一（中）
`.venv`(3.9.6 + numpy 2.0.2) 全绿，系统 `python3` 因缺 numpy 报 1 error。无 CI、无 `requirements.txt`/`pyproject.toml`，新机器上不可复现。

### R5｜交付文档结构缺口（中）
按 `edging/docs/README.md` 自定的理想结构，实际缺失：
- `00-foundations/` 缺 vision.md、principles.md
- `01-product/` 缺 positioning.md、prd.md、user-scenarios.md
- `03-system/` 缺 architecture.md、sampling-engine.md、reasoning-engine.md、storage-and-events.md
- `04-safety/` 缺 compliance-baseline-cn.md、pii-policy.md、forbidden-use-cases.md
- `05-research/` **整个目录不存在**
- `06-delivery/` 缺 milestones.md、backlog.md

### R6｜文档间自相矛盾（中）
`edging/docs/06-delivery/roadmap.md` 的 Current Blockers 写着「no machine-readable registry yet / no chosen first family set」，而 `goal-64d-384-seed.md` 与实测门禁显示 registry 已 64/64 + 384/384、结构 COMPLETE。roadmap 未随进度更新。

### R7｜诊断工具与正式引擎的边界需持续保持（低）
正式第一章主实现引擎已经明确为 Godot，UE5 是读取同一共享快照的正式对比实现。`edge-world Shared/Renderer.swift` 与 `preview3d` 的 SceneKit 目标属于历史客户端实验或诊断工具，不应再被描述为正式引擎候选。

### R8｜历史包袱（低）
`../GTAV` 占 12 GB 且已确认不可构建；`ai_toach`、`output` 与主线无关。不影响代码，只影响备份/检索成本。

### R9｜UE5 对比工程位于外置盘且无 Git 历史（中·高）
以下为首次审计时发现、现已由对比实现取代的历史状态：`/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` 当时的 6 个文件（60 行）全部是 `new-ue5-cpp-project.sh` 生成的官方模板原样内容：
`EdgeWorldUE.uproject`(180 B)、`Build.cs`(376 B)、`EdgeWorldUE.cpp`(144 B)、`EdgeWorldUE.h`(39 B)、两个 `Target.cs`。
- **零第一章实现**：无 `Content/`、无 `.uasset`/`.umap`、无 Gameplay C++ 类、无蓝图、无 `Config/`。
- **从未编译或启动过**：无 `Binaries/`、`Intermediate/`、`Saved/`；`DerivedDataCache/` 为 **0 B**（若 Editor 曾打开过工程，DDC 必有数据）。
- **无 git**：`git log` 报 not a repository，改动零历史保护。
- **不在任何进度文档里**：`EDGE_WORLD_PROGRESS.md` 与 `edge-world/doc/*` 均未提及 UE5 或 DevSSD 工作区。
- 引擎侧已就绪：UE 5.8.2 binary 版（含 `UnrealEditor`/`UnrealEditor-Cmd`）。源码编译路线在 09-17 时被 Epic 私有 GitHub 仓库权限挡住（见 `/Volumes/DevSSD/Unreal/README.md`）。
- 辅助脚本 4 个在 `/Volumes/DevSSD/Unreal/Tools/Scripts/`：`ue5-env.zsh`、`new-ue5-cpp-project.sh`、`clone-ue5-source.sh`、`build-ue5-source-mac.sh`。

**当前含义**：UE5 已不再是空模板，并已完成 C++ 运行时 UMG、玩家输入、异步 Ollama/确定性回退和快照热重载。实现仍位于外置盘且无 Git 历史；资产化关卡、截图/性能对比仍未完成。

---

## 五、下一步建议（按优先级）

### P0 — 今天就能做完，消除最大风险
1. **提交全部未提交工作**（R3）：把 14 项按主题拆 3 个 commit（`chapter-one runtime` / `subjective world` / `platform frontends`），推送 `feature/edge-world`。
2. **重写工程进度文档**（R1）：以本报告替换 `EDGE_WORLD_PROGRESS.md` 的 O3DE 内容，保留历史记录段落并明确标注"已废弃"。
3. **统一 Python 环境**（R4）：补 `requirements.txt`（numpy==2.0.2）+ 一个 `make test` / `scripts/test.sh` 统一入口，杜绝"系统 python 跑不过"。
4. **保护 UE5 对比实现**（R9）：为 `/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` 建立版本历史或纳入主工程可恢复方案。

### P1 — 本阶段必须做的决策
5. **执行 Godot↔UE5 对比计划**（R7/R9）：Godot 保持主实现，UE5 补齐 UMG、玩家输入、自动截图和性能指标；SceneKit 保持诊断用途。
6. **决策接线方式**（R2）：明确 `edging` 的 64D/384 是
   (a) 作为 `world_engine` 的**地形/事件生成前置**（家族→区域气质，爻位原型→当前状态原型），还是
   (b) 作为**玩家行为评分层**（回合结束→64D 向量→定数剧本），还是 (c) 两者。
   建议先做 (b)，因为它直接对应技术路线三阶段 2 的"定数"，且输入输出都是结构化 YAML/JSON，接线成本最低。
7. **打通原典数据单一来源**（R2）：以 `edging/.../classical-line-texts.v0.1.yaml`（384/384）为唯一权威，生成/校验 `engine/yijing_text.json`，消除"部分卦缺卦辞"的现状。
8. **更新 roadmap 与 blockers**（R6）：把已完成的 registry/transition/scorer 从 blocker 移入 done。

### P2 — 推进主线功能
9. 一阶段 4：在 Godot 中实现最小实体/交互系统与相机漫游，让程序化世界可被玩家进入。
10. 三阶段 2 收尾：实现"熵值"累计与"变数"触发，把 `deterministic_scorer` 的 uncertainty 输出接到 Chapter One 快照的 `decision` 段。
11. 补 `03-system/architecture.md`：把 A–H 八条轨道的边界、数据流、接口协议画成一张图（当前只有散文描述）。

### P3 — 清理
12. 归档或移出 `../GTAV`(12GB)、`ai_toach`、`output`，给 `edgeWorld` 顶层瘦身；同时把 `/Volumes/DevSSD/Projects/EdgeWorldGodot` 这个已被取代的骨架标记为废弃。

---

## 六、一句话总结

**代码进度已经跑在文档前面很远**：Chapter One 全链路（Python 运行时 → 规则门禁 → 共享快照 v2 → Godot 游戏引擎）已经跑通，SceneKit 提供诊断预览；edging 的 64D/384 结构层也有实测证据。但：

1. **两套体系彼此孤立**（edging 评分层与游戏运行时零引用）；
2. **主力代码尚未进 git**（14 项未提交，含 1042 行的 `subjective_world.py`）；
3. **顶层进度文档停在已废弃的 O3DE 路线**，没有准确记录 Godot 主实现与 UE5 正式对比实现的分工；
4. **UE5 已有交互对比实现，但位于外置盘且无 Git 历史**，仍存在成果丢失风险；
5. **外置 SSD 工作区长期处于视野之外**——Godot 骨架与 UE5 工程都在 `/Volumes/DevSSD`，不在 `edgeWorld/` 内。

**当前最该做的不是写新功能，而是"固定成果 + 索引全部工作区 + 拍板引擎主线"。**

---

## 附：完整工作区索引（含外置盘）

| 路径 | 内容 | 归属文档 |
|---|---|---|
| `/Users/yangacan/edgeWorld/edge-world` | Python 规则核心 + Godot 引擎 + SceneKit 诊断预览 + edging 层 | 部分（README 有） |
| `/Users/yangacan/edgeWorld/EDGE_WORLD_PROGRESS.md` | 顶层进度文档 | ❌ 已失真（O3DE 路线） |
| `/Users/yangacan/edgeWorld/GTAV` | GTA V 源码快照 12 GB | 仅有阻塞结论 |
| `/Volumes/DevSSD/Unreal/` | UE5 安装与第一章正式对比开发环境 | 本报告已澄清 |
| `/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` | UE5 第一章 C++ 对比实现 | `godot_ue5_comparison.md` |
| `/Volumes/DevSSD/Projects/EdgeWorldGodot` | Godot 验证骨架（已被取代） | ❌ 无 |
| `/Applications/Godot.app` + `edge-world/engine_platforms/godot` | Godot 第一章实现 | 仅 README 一句 |
| `/Users/Shared/Epic Games/UE_5.8` | UE 5.8.2 引擎二进制 | ❌ 无（在 DevSSD README 里） |
