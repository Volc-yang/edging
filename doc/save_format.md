# 存档与回放格式（Save & Replay Format）

状态：已实现 · 2026-09-21
相关代码：`engine/snapshot_store.py`、`engine/chapter_one_history.py`、`tools/chapter_one_history.py`

## 一、为什么需要

在引入本格式之前，`models/chapter_one_snapshot.json` 只保存**当前一轮**。前端一旦推进世界，
上一轮就永久消失——无法回放、无法审计、也无法迁移旧存档。同时，Godot 与 UE5 都可能在同一时刻
提交，读-改-写会互相覆盖（已实测：无锁时 4 轮塌缩为 1 轮）。

现在有三层，职责分明：

```text
models/
  chapter_one_snapshot.json          ← 活快照(唯一可被引擎读取的状态)
  chapter_one_snapshot.json.lock     ← 轮次锁(advisory flock)
  history/
    index.json                       ← 哈希链清单(唯一的可变部分)
    index.json.lock
    rounds/
      tick-000001.json               ← 每轮一份，写入后永不修改
      tick-000002.json
```

## 二、活快照

- 路径：`models/chapter_one_snapshot.json`
- schema：`edgeworld.chapter-one-snapshot.v2`
- 写入方式：临时文件 + `fsync` + `os.replace`（原子替换）
- 唯一写入者：Python 规则层（`tools/run_chapter_one.py`）。Godot / UE5 / SceneKit **只读**。
- 校验：损坏、未知 schema、`tick` 非正整数时**明确报错**，绝不静默把世界时间重置为第 1 轮。

## 三、轮次锁（跨进程）

- 锁文件：`<快照>.lock`（sidecar，不是快照本身——快照每次写入都会换 inode）
- 机制：`fcntl.flock(LOCK_EX|LOCK_NB)` + 轮询重试
- 覆盖范围：**整个读-改-写周期**，即
  `读当前 tick → Ollama/规则计算 → 写快照 → 归档该轮`
- 等待上限：`--lock-timeout`（默认 `--timeout + 60s`，确保能等到对方完成一次模型调用）
- 超时行为：退出码 **75（EX_TEMPFAIL）** 并输出 `{"error":"snapshot_lock_timeout"}`，前端可安全重试
- 实测：3 个并发进程提交同一快照 → tick 22 / 23 / 24，无丢失无重复

## 四、轮次归档

每轮一份不可变文件 `rounds/tick-NNNNNN.json`：

```json
{
  "history_schema_version": "edgeworld.chapter-one-history.v1",
  "tick": 2,
  "source": "ollama:llama3.2:latest",
  "recorded_at": "2026-09-21T02:11:03+00:00",
  "snapshot": { "…完整的已批准快照…" }
}
```

- 写入后不再修改；同一 tick 重复归档是**幂等**的（返回原条目，保留原始存档）
- `source` 记录该轮由谁产生：`offline` 或 `ollama:<model>`

## 五、索引与哈希链

`history/index.json`：

```json
{
  "schema_version": "edgeworld.chapter-one-history.v1",
  "chain_head": "<最后一轮的 entry_hash>",
  "updated_at": "…",
  "entries": [
    {
      "tick": 1,
      "file": "rounds/tick-000001.json",
      "sha256": "<归档文件字节的 sha256>",
      "prev_hash": null,
      "entry_hash": "sha256(prev_hash|tick|sha256)",
      "chapter_score": 0.9664,
      "encounter": "无妄",
      "changed_hexagram": "讼",
      "decision_source": "rule_fallback",
      "source": "offline"
    }
  ]
}
```

`entry_hash = sha256(f"{prev_hash or ''}|{tick}|{round_sha256}")`，形成哈希链：

- 篡改任一归档文件 → `sha256` 不匹配
- 从清单删除任一轮 → `prev_hash` 断链 + 出现孤儿文件
- 删除归档文件 → `file missing`
- `chain_head` 与最后一条不一致 → 清单被改写

`python3 tools/chapter_one_history.py verify` 会一次性报告全部问题（`ok: false` + `problems[]`），
退出码非 0 时可用于 CI 或发布前门禁。

## 六、回放

- 列举可用轮次：`python3 tools/chapter_one_history.py list`
- 读取某一轮：`python3 tools/chapter_one_history.py show 7`
- 只看某字段：`… show 7 --field encounter.governing_line.name`
- 导出回放包：`python3 tools/chapter_one_history.py export-replay <输出路径>`
  - schema：`edgeworld.chapter-one-replay.v1`
  - 内容：`source_index` + `rounds[]`（按 tick 升序的完整快照）
- 确定性重跑：`python3 tools/run_chapter_one.py --offline --tick N`
  （`--tick N` 是固定时序入口；`--advance` 才是推进下一轮）

## 七、存档迁移策略

原则：**未知或更新的 schema 一律拒绝，绝不猜测解释。**

- 所有被打包的数据都带显式 `schema_version` / `history_schema_version`
- 迁移通过显式注册表完成：`register_migration(from_schema, to_schema, fn)`
- `migrate_payload(payload, target)` 会循环应用已注册迁移，遇到未注册来源即抛
  `SnapshotError("no migration registered for schema …")`，并列出已知来源
- 检测到循环迁移同样报错（`migration cycle detected`）
- 命令行入口：`python3 tools/chapter_one_history.py migrate <tick> --to <schema>`

> 当前仓库内**尚不存在旧 schema 的存档**，因此迁移注册表是空的。这不是缺口，而是纪律：
> 一旦出现旧存档，必须写一条真实迁移并配套测试，而不是让运行时"尽力而为"地误读。

## 八、版本与兼容矩阵

| 数据 | 当前 schema | 兼容策略 |
|---|---|---|
| 活快照 | `edgeworld.chapter-one-snapshot.v2` | 旧 schema 报错；需迁移后用 `--tick N` 重放 |
| 轮次归档 | `edgeworld.chapter-one-history.v1` | 同上；归档本身不因快照 schema 变化而改变 |
| 回放包 | `edgeworld.chapter-one-replay.v1` | 只读导出格式，可长期保存 |
| 决策提案 | `edgeworld.chapter-one-decision.v2` | 模型输出契约，非法即回退到确定性规则 |

## 九、待办

- 归档目录体积会随轮次增长，后续需要定义压缩或分段归档策略（例如按 100 轮分片）。
- 前端（Godot / UE5）尚未接入历史浏览 UI；当前通过 CLI 与回放包消费。
