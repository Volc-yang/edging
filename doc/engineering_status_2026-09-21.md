# Edge World 工程任务与进度分析（2026-09-21）

分析时间：2026-09-21
分析对象：`/Users/yangacan/edgeWorld/edge-world`（主工作区）+ `/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE`（UE5）+ `/Volumes/DevSSD/Projects/EdgeWorldGodot`（旧骨架）
数据来源：源码清点 + **实际执行**测试/一致性门禁/命令行校验，非文档转述。
版本说明：本文件取代 `engineering_status_2026-09-20.md`（该版在 UE5 轨道大幅推进前撰写，且遗漏外置 SSD 工作区）。

---

## 一、实测证据（本次真实执行）

| 验证项 | 命令 | 结果 |
|---|---|---|
| Python 测试（venv） | `./.venv/bin/python -m unittest discover tests` | **90 tests OK** |
| Python 测试（系统 python3） | `python3 -m unittest discover tests` | FAILED 1 error（系统 3.9.6 缺 numpy） |
| Godot 第一章 | `Godot --headless --path engine_platforms/godot --quit` | `EDGEWORLD_GODOT_CHAPTER_ONE_VALID schema=v2 spirits=8 primary=渐 changed=升 houtian=thunder/E/3` 退出码 0 |
| UE5 合约校验 | `UnrealEditor-Cmd … -run=EdgeWorldSnapshot -unattended -nop4 -nullrhi` | `EDGEWORLD_UE_CHAPTER_ONE_VALID schema=v2 spirits=8 primary=渐 changed=升 houtian=thunder/E/3`，**Success 0 error 0 warning**，退出码 0 |
| Godot↔UE5 一致性 | `python3 tools/validate_godot_ue5_parity.py` | **`status: match`**（schema/灵体数/本卦/变卦/后天主灵/方位/洛书数 逐项一致） |
| UE5 编译产物 | `Binaries/Mac/libUnrealEditor-EdgeWorldUE.dylib` | 存在，09-21 09:33 重新编译 |
| UE5 实机运行 | `Saved/Screenshots/MacEditor/HighresScreenshot0000{0,1}.png` + `EditorPerProjectUserSettings.ini` | 存在，Editor 中实际跑过并在 09-21 09:35 仍被使用 |
| edging 结构门禁 | `ruby bin/validate_spacetime_abstractions.rb --complete` | PASS / COMPLETE（64/64、384/384、2304/2304、320/320） |
| 无真实崩溃 | `Crashes/`、`DiagnosticReports` 无 Unreal 条目 | 30 个 `CrashReportClient` 目录为每次会话的正常残留，**非崩溃** |

---

## 二、轨道清点与规模（当前）

| 轨道 | 路径 | 规模 | 状态 |
|---|---|---|---|
| A. Python 世界引擎核心 | `engine/*.py` | 4164 行 / 11 模块 | 可用，测试覆盖 |
| B. 第一章规则运行时 | `engine/chapter_one_runtime.py` | **740 行**（09-20 为 523） | 规则门 + 卦爻抽象 + 世界反馈闭环 |
| C. 主观世界层 | `engine/subjective_world.py` | **1086 行**（09-20 为 1042） | 意识/熵/卦值更新已接入反馈闭环 |
| D. Godot（第一章**主实现**） | `engine_platforms/godot/` | 347 行 GDScript | headless 合约通过，含 UMG 等价控制面板 |
| E. UE5（第一章**对比实现**） | `/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` | **960 行 C++ / 13 文件** | 已编译、已实机运行、Commandlet 通过 |
| F. SceneKit 诊断预览 | `preview3d/` + `edge-world Shared/` | 2344 行 Swift | 明确**不计为**游戏引擎实现 |
| G. 原型评分层 | `edging/`  Ruby + YAML | 1230 行 Ruby + 26 篇文档 | 结构 100%；**原典数据已打通到运行时** |
| H. 一致性门禁 | `tools/validate_godot_ue5_parity.py` | 99 行 + 对应测试 | 可一键验证两端一致 |
| I. 旧 Godot 骨架 | `/Volumes/DevSSD/Projects/EdgeWorldGodot` | 2 文件 | 已被 D 取代，未标记废弃 |
| J. GTA V 源码 | `../GTAV` | 12 GB | 确认不可构建，历史包袱 |

UE5 核心类：`FChapterOneSnapshotReader`（加载校验 JSON）、`AChapterOneWorldActor`（相机/光照/八灵球体/标签）、`AEdgeWorldGameMode`（启动世界 Actor）、`UChapterOneControlWidget`（UMG 受限输入 + 异步调用共享规则门）、`UEdgeWorldSnapshotCommandlet`（无界面合约校验）。

---

## 三、本轮新增进度（09-20 分析之后 → 09-21）

| # | 交付物 | 证据 | 状态 |
|---|---|---|---|
| 1 | **UE5 轨道从"空壳"到完整实现** | 13 个 C++ 文件 960 行；已编译；实机截图；Commandlet 通过 | ✅ 完成 |
| 2 | UE5 异步调用共享规则门 + 原位重建八灵 | `UChapterOneControlWidget`（254 行） | ✅ 完成 |
| 3 | **卦爻抽象与世界反馈闭环** | 快照新增 `encounter.abstraction`、`governing_line`、`world_response` | ✅ 完成 |
| 4 | 主导爻按证据选取 + 引用完整卦爻辞 + 预判 | `chapter_one_runtime.py` 740 行；README 契约成文 | ✅ 完成 |
| 5 | 主观世界实际更新 + 三端表现同步 | 目标灵体意识/自洽/熵/卦值更新；Godot、UE5、SceneKit 按同一 `world_response.control` 改变尺寸/位移/发光 | ✅ 完成 |
| 6 | **原典语料打通**（上轮 P1 建议第 7 条） | 新增 `edging/bin/sync_engine_yijing_text.rb`；`engine/yijing_text.json` 现含 **64/64 卦辞 + 64/64 大象 + 384/384 爻辞** | ✅ 完成 |
| 7 | tick 推进缺陷修复 | 新增 `--advance`；三引擎统一；`--tick N` 保留给确定性回放 | ✅ 完成 |
| 8 | Godot↔UE5 一键一致性门禁 | `tools/validate_godot_ue5_parity.py` + `tests/test_godot_ue5_parity_tool.py` | ✅ 完成 |
| 9 | 工作日志体系 | `doc/worklog_2026-09-20.md`、`worklog_2026-09-21.md`、`godot_ue5_comparison.md` | ✅ 完成 |
| 10 | 渲染对照产物 | `artifacts/render_compare/`（Godot PNG×6 + WAV×2，含修复前后对比） | ✅ 完成 |
| 11 | 测试规模 | 83 → **90** 项（新增 CLI/一致性工具/文本测试） | ✅ 完成 |

**关键判断**：上轮报告指出的两个最大结构性问题之一（R2 原典数据未打通）**已被解决**；UE5 从"只到脚手架"（当时实测 60 行、DDC 0 B、从未编译）推进到**可编译、可运行、可合约校验、与 Godot 逐项一致**。

---

## 四、按原始开发计划的总体进度

| 计划项 | 计划工期 | 完成度 | 说明 |
|---|---|---|---|
| 一阶段 1 项目基础架构 | 1–2 周 | ~75% | 多端目标 + 一键一致性门禁 |
| 一阶段 2 程序化世界生成 | 3–4 周 | ~60% | `world_engine` 八卦地形/群系完整；UE5/Godot 侧八灵场景已建，但世界地形未资产化 |
| 一阶段 3 四象时间系统与渲染管线 | 2–3 周 | ~50% | 时钟/相位码完成；昼夜光照 Shader 未做 |
| 一阶段 4 实体与交互原型（ECS + 漫游） | 2–3 周 | ~20% | 八灵场景含相机与点击反馈，但无正式 ECS 与自由漫游 |
| 二阶段 服务端与"降神"玩法 | 8–10 周 | **0%** | 无服务端、无 WebSocket、无 DB |
| 三阶段 1 道生万物生命周期 | 4–6 周 | ~40% | 意识/熵/卦值已可被玩家行为驱动更新 |
| 三阶段 2 定数与变数系统 | 5–7 周 | ~55% | 64D/384 结构 100%；**评分器仍未接入运行时**，"熵/变数触发"未实现 |
| 四阶段 内容填充 | — | 0% | — |
| 五阶段 测试优化部署 | — | ~35% | 90 单测 + 3 个可执行门禁；无 CI |
| **计划外主线：第一章「万物有灵」三端一致性** | — | **~90%** | 规则层唯一权威 + 三端消费 + 一键 parity 门禁 |

---

## 五、剩余问题与风险（按严重度）

### R1｜主力工作仍未进 git（**高，且已恶化**）
未提交项从 14 项增至 **26 项**，且新增了全部 UE5 之前的核心资产：

```
engine/chapter_one_runtime.py(740)  engine/subjective_world.py(1086)
tests/(14 文件, 1370 行)             tools/(917 行)
models/chapter_one_snapshot.json    engine_platforms/(Godot 主实现)
preview3d/Sources/EdgeWorldChapterOne/   doc/(worklog/comparison/cosmology/validation)
artifacts/render_compare/           edging/bin/sync_engine_yijing_text.rb
doc/engineering_status_2026-09-2{0,1}.md
```
分支 `feature/edge-world` 停在 `de2794b`（09-17），**之后所有进展零版本保护**。
另：UE5 工程 `/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` **完全无 git**。

### R2｜顶层进度文档仍未修正（中）
`/Users/yangacan/edgeWorld/EDGE_WORLD_PROGRESS.md` 依旧停在已废弃的 O3DE 路线。
反观 `edge-world/doc/` 内部已有高质量 worklog 体系（09-20、09-21），**信息只在上游缺失**。

### R3｜edging 64D/384 评分器仍未接入运行时（中）
原典数据这一半已打通（`sync_engine_yijing_text.rb`），但**评分器本体仍未进入第一章运行时**。
技术路线"三阶段 2 定数与变数"的核心（回合结束→64D 行为向量→定数剧本）尚无实现。

### R4｜跨进程并发写入未定义（中）
worklog 09-21 自己列出的待办：Godot 与 UE5 同时提交时的快照写入策略未验证，可能需要跨进程锁。两端都直接写同一个 `models/chapter_one_snapshot.json`。

### R5｜多 tick 历史/回放索引/存档迁移无正式格式（中）
`--advance` 已实现轮次推进，但历史轮次未归档，无法回放或迁移存档。

### R6｜UE5 工程未资产化（低·中）
`Content/` 为空，仍用引擎模板地图 `Template_Default`；八灵由 C++ 运行时生成。UMG 主题、可访问性、响应式布局、资产化关卡、灵体交互组件均未做。

### R7｜环境不可复现（低·中）
无 `requirements.txt` / `pyproject.toml`；系统 python 3.9.6 缺 numpy 会让 90 项测试出现 1 个 error；无 CI。

### R8｜无性能/资源对比数据（低）
`godot_ue5_comparison.md` 已列出"启动耗时、内存、帧时间、资源构建成本"为下一阶段比较项，尚未采集。

### R9｜目录散落与废弃物（低）
`/Volumes/DevSSD/Projects/EdgeWorldGodot`（旧骨架）未标记废弃；`../GTAV` 12 GB；`ai_toach`、`output` 与主线无关。

---

## 六、下一步建议

### P0 — 立刻做，消除最大风险
1. **提交全部工作**（R1）：26 项按主题分 4 个 commit（`chapter-one runtime` / `subjective world + tests` / `engine platforms (godot+scenekit)` / `docs + artifacts`），推送 `feature/edge-world`。
2. **给 UE5 工程建 git**（R1）：`/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE` 先 `git init` + 首次提交（`.gitignore` 已在，排除 `Binaries`/`Intermediate`/`Saved`/`DerivedDataCache`）。
3. **重写顶层进度文档**（R2）：把 `EDGE_WORLD_PROGRESS.md` 的 O3DE 段落标注为已废弃，改为指向 `edge-world/doc/worklog_*.md` 与 `engineering_status_2026-09-21.md`。
4. **补 `requirements.txt` + 统一测试入口**（R7）。

### P1 — 补齐第一章收尾（worklog 自己列的清单）
5. 验证 Godot 与 UE5 同时提交的并发写入策略，必要时加跨进程文件锁（R4）。
6. 定义多 tick 历史、回放索引、存档迁移的正式格式（R5）。
7. 在两端各连续点击三轮，确认界面轮次与快照 `tick` 同步（worklog 待办）。

### P2 — 拍板与推进主线
8. **决策 edging 评分器接线方式**（R3）：建议先做"回合结束→64D 向量→定数剧本"（对应三阶段 2），输入输出均为结构化 YAML/JSON，接线成本最低。
9. 拍板正式客户端主线：Godot（现为主实现）是否长期主线？UE5 是对比目标还是后续高清管线？
10. 采集 UE5 vs Godot 的性能数据（启动耗时/内存/帧时间/构建成本），为选型提供依据（R8）。
11. 一阶段 4：最小 ECS + 相机漫游；一阶段 3 收尾：昼夜光照。

### P3 — 清理
12. 标记 `/Volumes/DevSSD/Projects/EdgeWorldGodot` 废弃；归档 `../GTAV`、`ai_toach`、`output`。

---

## 七、结论

**第一章「万物有灵」已经是可运行、可验证、跨引擎一致的完整闭环**：Python 规则层是唯一权威，Godot（主实现）与 UE5（对比实现）消费同一份 v2 快照，一键 parity 门禁保证逐项一致（本次实测 `status: match`，本卦渐→变卦升、后天震/东/洛书三，三方完全相同），原典语料 64/64 卦辞 + 384/384 爻辞完整接入，主观世界状态可被玩家行为实际驱动。

**当前瓶颈不是技术，而是工程纪律**：26 项主力工作未提交、UE5 工程无版本控制、顶层进度文档指向已废弃路线。这三项都是当天可完成、零风险的。

**下一步价值最高的两件事**：① 立刻把成果固定进 git；② 把 edging 的 64D/384 评分器接进运行时，让"定数与变数"这条独特玩法真正跑起来——目前它是唯一一条"结构做完但产品 0%"的轨道。
