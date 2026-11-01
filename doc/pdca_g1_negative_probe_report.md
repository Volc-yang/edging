# G1 树与混沌进程错误矩阵

状态：2026-11-01，v0.1；固定输入 `86aea9d`。本卡只检查两个 Python worker 的 JSONL 负例，不检查 UE、Genesis、AI 或产品门。使用 DevSSD 上独立状态目录，没有接触用户正在运行的 UE/Worker。

## Plan / Do

从新目录分别启动树与混沌 worker，先在单独进程执行 `status` 和一条合法的 tick 1 `advance`；再从相同状态目录重启，顺序发送八条负例。每条均写入唯一 `request_id`，并保存原始请求、响应、启动命令、退出码和负例进程前后的全部状态文件 SHA256。脚本与原始文件位于 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/g1-negative-6hji9k7o/`；运行命令为 `python3 probe.py`，准确 Python 可执行文件和 worker argv 记在原始 JSON。

首次尝试的混沌启动参数误用了 `world_id=chaos-negative`，而固定初态文件的 ID 为 `chaos-demo`；worker 如预期返回 `startup_error/world_mismatch`、退出码 2。原始记录保留于 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/g1-negative-65pswn3j/chaos/raw.json`。随后用匹配的 ID 和新的状态目录重跑完整矩阵。首次尝试不计为八项检查的通过。

## Check：实际错误与状态隔离

| 负例 | 树预期/实际 | 混沌预期/实际 |
| --- | --- | --- |
| 已使用 `command_id` 携带不同输入 | `command_id_conflict` / 相同 | `command_id_conflict` / 相同 |
| 过期 `expected_revision` | `revision_conflict` / 相同 | `revision_conflict` / 相同 |
| 未保留 tick 99 | `history_missing` / 相同 | `history_missing` / 相同 |
| tick 1 但 watermark 0 | `watermark_mismatch` / 相同 | `watermark_mismatch` / 相同 |
| 错误 world ID | `world_not_found` / 相同 | `world_mismatch` / 相同 |
| 协议版本 99 | `unsupported_protocol` / 相同 | `unsupported_protocol` / 相同 |
| 不支持的演化规则版本 | `unsupported_rules` / 相同 | `unsupported_rules` / 相同 |
| 非法 JSON 行 | `invalid_json` / 相同 | `invalid_json` / 相同 |

两类 worker 各 8/8 次返回 `ok:false` 和预期错误码，负例进程退出码均为 0。每类进程的状态目录文件 SHA256 字典在八条请求前后相同；这些被拒绝的请求没有修改持久状态。此结论仅覆盖所列负例和当前单机 Python 实现，不代表错误全集、并发竞争或 UE 客户端处理已通过。

| 原始文件 | SHA256 |
| --- | --- |
| `tree/raw.json` | `ffecb8aa094ee65cf66f0fcb4a4b345fde66145e1910867983d905c25c66f228` |
| `chaos/raw.json` | `478fc9c48d52361d01ab170af2967be067539f1f0057c317b71426aae4899cfd` |
| `summary.json` | `d487a9e107a3a4a757573341db152208de4a84f6e2a3fd44a02d2dab30ff3476` |
| `probe.py` | `be6442f4e8beabfcac0f0b1a8510f2349985f499338d65bfbbe2310fbc4031ec` |
| 首次混沌启动错误 `chaos/raw.json`（前述旧目录） | `db9aadde248243b9e69f5f93a9ea700d715c12f9f22a5f8583e94b400cc536ea` |

## Act

G1 的树/混沌错误矩阵可记为有限通过，并保留 `world_not_found` 与 `world_mismatch` 的现有差异；不修改 wire code 来强行统一。下一个接口门仍需确定本版本必需领域，检查 UE 调用点的结果身份拒绝路径；Genesis 与用户产品范围尚待裁决。若原始文件跨机器不可达，需先按哈希转存，不能仅靠本报告代替复核。
