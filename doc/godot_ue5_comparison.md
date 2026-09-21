# Godot 与 UE5 第一章对比验证

## 定位（已定，2026-09-21）

| 平台 | 角色 | 说明 |
|---|---|---|
| **Godot 4.7** | **第一章主引擎** | 承担当前主循环：玩法迭代、规则验证、ECS、漫游。冷启动 0.244 s，见 `engine_performance.md` |
| **UE5 5.8.2** | **高清管线候选** | 不承担当前主循环。用于引擎无关性验证，以及玩法稳定后的高清渲染管线 |
| SceneKit | 开发诊断预览 | **不计为**游戏引擎实现 |

**决策依据**：`doc/engine_performance.md` —— 第一章自身载荷同量级（60 KB GDScript vs 84 KB C++），
成本全在引擎侧（冷启动 43×、内存 7.9×、磁盘 128×）。玩法迭代期 Godot 的优势会逐轮复利，
而 UE5 的画面优势在当前阶段（无美术资产、`Content/` 为空）无法兑现。

**该决策可延后而不返工**：两套引擎都只消费同一份已批准快照，换引擎只需重新实现消费端；
`tools/validate_godot_ue5_parity.py` 持续保证两端行为一致。

两套游戏引擎都不能自行计算或修改卦象，只能消费 Python 规则层批准的
`edgeworld.chapter-one-snapshot.v2`。

## 当前共同能力

| 能力 | Godot | UE5 |
|---|---:|---:|
| 校验 schema v2 | 已实现 | 已实现 |
| 校验先天世界/后天变化 | 已实现 | 已实现 |
| 校验八个基础灵体 | 已实现 | 已实现 |
| 读取本卦、动爻、变卦 | 已实现 | 已实现 |
| 显示八灵环形场景 | 已实现 | 已实现（C++ Actor） |
| 显示遭遇摘要 | 已实现 | 已实现（运行时 HUD 文本） |
| Headless 合约检查 | 已实现 | 已实现（Commandlet） |
| 八类玩家动作、强度、表达输入 | 已实现 | 已实现（运行时 UMG） |
| 调用 Ollama/确定性回退 | 已实现 | 已实现（异步子进程） |
| 快照更新后重载八灵与遭遇 | 已实现 | 已实现（原位重建） |
| 每次玩家提交自动推进世界 tick | 已实现 | 已实现 |
| 显示主导爻、卦辞、爻辞和预判 | 已实现 | 已实现 |
| 执行共享世界控制并反馈状态 | 已实现 | 已实现 |
| 目标灵体尺寸、位移、发光响应 | 已实现 | 已实现（含响应点光源） |

## UE5 工程

路径：`/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE`

核心类：

- `FChapterOneSnapshotReader`：加载和验证共享 JSON。
- `AChapterOneWorldActor`：生成相机、光照、八灵球体和标签。
- `AEdgeWorldGameMode`：启动第一章世界 Actor。
- `UChapterOneControlWidget`：收集受约束的玩家介入，异步调用共享规则门并重载快照。
- `UEdgeWorldSnapshotCommandlet`：无界面合约校验。

## 一键对比

```bash
python3 tools/validate_godot_ue5_parity.py
```

脚本分别启动 Godot headless 和 UE5 Commandlet，并与源快照逐项比较：

- schema 版本
- 灵体数量
- 本卦
- 变卦
- 后天主灵
- 后天方位
- 洛书数

只有三方完全一致时返回 `status: match`。

## 当前验证结果

```text
Godot: schema v2 / 8 spirits / 讼 → 巽 / water / N / 1
UE5:   schema v2 / 8 spirits / 讼 → 巽 / water / N / 1
status: match
```

UE5.8 Editor Development 目标已成功编译。游戏模式已加载 `EdgeWorldGameMode`，运行日志出现
`EDGEWORLD_UE_CHAPTER_ONE_READY`，证明八灵 Actor 路径实际执行，而不只是 JSON Commandlet 可用。
本地 `llama3.2:latest` 已通过 UE5 所复用的共享入口完成动态样例：玩家动作 `flow=0.6`，
规则门批准后得到本卦讼、变卦巽、后天坎/北/洛书一；两个引擎对新快照仍为 `match`。

渲染对照已完成一轮缺陷修复：Godot 使用明确的中文字体文件；UE5 使用八灵颜色材质、
面向相机的英文 3D 标签，并在正确的 Slate 重建阶段创建 UMG。UE5 面板实际触发下一轮后，
共享结果变为无妄→观、后天震/东/洛书三，Godot 与 UE5 再次返回 `match`。

2026-09-21 修复了连续提交停留在 `tick=1` 的问题。Godot、UE5 和 SceneKit 的推演按钮
现在统一调用 `--advance`，从当前 v2 快照推进一轮；`--tick N` 继续保留给确定性回放。
真实 Ollama 连续验证得到第 2 轮随→同人、第 3 轮噬嗑→履，两个引擎对第 3 轮仍为 `match`。

同日新增卦爻抽象与世界反馈闭环。Python 规则层统一选择主导爻、引用完整卦爻辞、生成预判，
并实际更新目标灵体的主观状态；两个引擎只消费 `world_response.control`，不自行解释经典。
第 7 轮颐→蒙、震/东/洛书三再次通过 `status: match`；随后本地 Ollama 第 8 轮实测得到
复卦六四“中行独复”→贲，并将震发控制应用于震灵。

## 下一阶段比较项

- 同一快照下的八灵空间位置、颜色与标签一致性。
- Godot 与 UE5 的相机操作和灵体点击反馈。
- 启动耗时、内存、帧时间和资源构建成本。
- UMG 的视觉主题、可访问性与响应式布局。
- UE5 资产化关卡和灵体交互组件。
- 两套引擎的自动截图与视觉差异报告。
