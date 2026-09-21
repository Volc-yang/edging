# 定数层：edging 64D/384 确定性评分器接入第一章

状态：已实现 · 2026-09-21
相关代码：`engine/destiny_layer.py`、`engine/chapter_one_runtime.py`
相关数据：`edging/docs/02-domain-model/*.v0.1.yaml`、`edging/bin/deterministic_scorer.rb`

## 一、为什么接、接的是什么

在接入之前，项目里有一条"结构 100%、产品 0%"的轨道：`edging` 的 64 卦家族向量
（64D）、384 爻位原型、320 条相邻转移与确定性评分器全部完工，但游戏运行时**一处都没有引用**
（已 grep 验证为孤立体系）。技术路线第三阶段"定数与变数"因此无法启动。

本层把评分器接进第一章运行时，做法是**只读投影**，而不是让 edging 参与卦象决定。

## 二、不可动摇的顺序

```text
先天世界 → 玩家介入 → Ollama 受限压力 → 后天定动爻 → 本卦/主导爻/变卦
                                                          ↓
                                            规则层下发受限世界控制、更新主观状态
                                                          ↓
                                              ★ 定数层读这一轮已批准的快照
                                                          ↓
                            10 维特征向量 → edging 确定性评分器 → 64 家族 + 384 原型读数
```

铁律（由测试强制）：

- 定数层**在整轮结束后**才运行，输出挂在快照最后一层 `destiny`
- 它**不能**改变本卦、动爻、变卦、世界状态或灵体主观状态
  （`test_destiny_does_not_change_the_hexagram_or_the_world_state` 会删掉两边的 `destiny`
  字段后逐字节比较整轮结果，必须完全相同）
- 它**不做** LLM 调用，纯确定性：同一快照必然得到同一读数

## 三、十维特征向量的推导（全部取自已批准快照）

`edging` 的 `feature-schema.v0.1.yaml` 定义十个维度。下表是每个维度的**唯一来源**，
实现里以 `destiny.derivation` 逐条写进快照，可审计：

| 维度 | 推导 | 来源 |
|---|---|---|
| `agency` 主动性 | 0.5×玩家动作轴压力 + 0.5×八轴峰值压力 | `encounter.abstraction.combined_action_pressures` |
| `visibility` 外显度 | 八灵 `consciousness` 均值 | `spirits[].entity.signature.consciousness` |
| `resource_mobilization` 资源动员 | 0.5×已激活轴占比(压力≥0.2) + 0.5×八轴压力均值 | 同上压力表 |
| `stability` 稳定性 | 八灵 `coherence` 均值 | `spirits[].entity.signature.coherence` |
| `risk_exposure` 风险暴露 | 八灵 `entropy` 均值 ÷ 满量程 0.05 | `spirits[].entity.signature.entropy` |
| `momentum` 动能 | 0.5×动爻比例 + 0.5×八轴压力均值 | `encounter.changing_positions` |
| `constraint_pressure` 约束压力 | (6 − 主导爻位) ÷ 6 | `encounter.governing_line.position` |
| `coordination` 协调度 | 1 − 八灵 \|阴−阳\| 均值 | `signature.yin_intent / yang_intent` |
| `timing_maturity` 时机成熟度 | 0.5×先天相位进度 + 0.5×本轮循环是否完成 | `tick`、`cycle.completed` |
| `governance_capacity` 治理能力 | 0.5×章内评分 + 0.5×末态自洽 | `validation.score`、`cycle.final_integrity` |

所有值 `clamp(0,1)`；缺失字段退化为中性值而**不报错**，因此任何一轮都能产出读数。

## 四、输出（写入快照的 `destiny` 段）

- `schema_version`: `edgeworld.chapter-one-destiny.v1`
- `source`: `edging-deterministic-scorer` / `unavailable` / `disabled`
- `feature_vector` + `derivation`: 十维读数与逐条依据
- `top_families`：前 3 个家族（`family_id` / `name_cn` / `score` / `max_prototype_score` / `local_coherence`）
- `top_prototypes`：前 5 个爻位原型（`prototype_id` / `line_index` / `state_name` / `score`）
- `uncertainty`：`overall` / `top_family_gap` / `top_prototype_gap` / `family_entropy_proxy` / `prototype_conflict_flag`
- `probe_target`：最该进一步探明的一个维度及理由
- `explanation_basis`：各项 schema 版本
- `validation_status` 与 `validation`：评分器自身的输入校验结果

**刻意不写入快照**：64 格家族分布与 384 格原型分布。它们会把快照撑大近一倍，且对玩法无用；
需要完整分布时直接调用评分器。

## 五、降级与纪律

- 找不到 `ruby` 或评分器脚本 → `source: "unavailable"` + `reason`，**轮次照常完成**，
  既不报错也**不伪造**读数。这与项目既有的 `canonical_text_available` 标记同一原则。
- 评分器超时（默认 30s）、退出码非 0、输出非法 JSON → 同样降级为 `unavailable`。
- 运行时禁用：`ChapterOneRuntime(..., destiny=False)`，或 CLI 不传评分器所在仓库根
  （`EDGEWORLD_SCORER` / `EDGEWORLD_RUBY` 可覆盖路径）。
- `subject_type` 固定为 `non_human_object`：**分析对象是世界/项目，不是人**，符合 MVP 范围里
  "非人对象分析"这条低风险流程，避免把系统包装成对人做画像或预测。

## 六、实测样例

`--offline --tick 7`（本卦颐 → 变卦蒙，与工作日志记录一致）：

```text
source            : edging-deterministic-scorer
validation_status : valid
scorer_version    : 0.1

feature_vector    : agency 1.0 / visibility 0.9007 / resource_mobilization 0.2094
                    stability 0.8081 / risk_exposure 0.4640 / momentum 0.2510
                    constraint_pressure 0.5 / coordination 0.6919
                    timing_maturity 0.9286 / governance_capacity 0.8194

top_families      : 乾(0.0182) 坤(0.0175) 大有(0.0174)
top_prototypes    : 乾·九五 central command (0.8131)
                    大有·上九 heavenly protection (0.7629)
                    坤·六五 noble receptivity (0.7627)
uncertainty       : overall 0.6870, prototype_conflict_flag true
probe_target      : agency
```

快照体积从约 36 KB 增至约 40 KB。

## 七、下一步

- 让前端（Godot / UE5）显示 `destiny` 读数：目前只写进快照，界面尚未消费。
- 用 `uncertainty` 与 `probe_target` 驱动**"变数"触发**：高不确定性或
  `prototype_conflict_flag` 为真时，生成一次探明性的世界事件。
- 用多轮 `top_families` 序列做**"定数"剧本**：回合序列 → 家族迁移 → 下一世开局条件。
- 评测：让 `probe_target` 真正参与下一轮的观测选择，形成主动采样闭环。
