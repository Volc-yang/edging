# I22 C：独立方案、源码、执行卡与实际证据审查

2026-11-10；review branch `codex/i22-review`，worktree
`/Users/yangacan/edgeWorld/edge-world/.worktrees/i22-review`，基线 `d194b4b`。
仅本目录报告；未启动 UE、GPU、Genesis、worker 或界面，未写 DevSSD，未公开发布。

结论：**接受有界 partial 迭代证据；不接受 D3-IMPORT 完成，不 merge 源实现。**
P2 是安装版 UE 5.8.3 的临时技术 fixture 能力通过；没有保存真实 I20 资产，
没有新进程 reload、真实 I20 材质负例、运行时、Metal 或写实画质验收。

## 审查链

- C0 已接受冻结方案，见 `plan-review.json`。
- 初版源码 `99ea747f3b703a7454e6629e1b9ea4b44bf81013`：独立 6 CPU、真实只读
  preflight 及 API 审查通过，见 `c1-source-CPU-review.json`、`installed-API-precheck.json`。
- P1 卡 `973d60af9eed1818bd0104b2a15930c0c4a47b8ddf4783b09b9844266e00ddaa`
  独立审定；真实 parent wait **255**，非 forced，无残留。结果为纹理恢复失败。
  原件没有记录实际差异字段，也不能排除 finally 覆盖先前异常，不能补写推断为事实。
- 窄修源码 `877696e7ef61a2fbfbc50fb0cd88ba10ceacb644`：独立核读本机
  `Texture.cpp:772–778`，TC_Masks/Normal 会将 sRGB 置 false；恢复改为
  compression → sRGB → flip。全字段和尺寸比较仍严格相等；保留 primary traceback、
  逐 clone before/after/diff 和原 Engine getter/包字节检查。独立 6 CPU 与 AST 通过，
  见 `c1-probe02-source-review.json`、`c1-probe02-cpu.txt`。
- P2 精确卡 `edfab7084de3a1c74c51a6ae4884c3057c07f13ebd6d0b75496f149973d14f6b`
  的 818 pins、argv/env、job/source、空 Content 均独立核对，见
  `c1-probe-02-card-acceptance.json`。真实 PID 86365，parent wait **0**，normal、
  非 forced；真实 subsystem、mesh/texture 严格恢复、原 Engine getter/包字节、
  Alpha 断开/恢复和非 Nanite 策略通过，见 `c2-probe-02-native-review.json`。
- Import-02 卡 `f2eb47cf8a403e7784cf0456f1becb4248d5a4f73bc5ab32e99cc081202ef6a1`
  仅准备并绑定 P2。剩余约 130.8 秒不足该卡 120 秒加 30 秒封存预留，root
  作 **NO-GO**；该卡未获 C1、未启动 UE、无 result，不再缩限或重置 clock。
  旧 a1 未执行，新进程 reload 未准备或执行。

## C2 封存复核

`check_run_evidence.py` 实际成功运行，详见 `c2-run-review.json`：重算两阶段共
818 唯一输入 pins；34 份 I20 原件完整不变；重解析 quiet/final 原始进程清单均无
相关存活；p1/p2/a1/a2 的实际项目 Content 全为空，无 uasset/sidecar。
274 个 regular 文件合计 **27,805,158 B**，DDC **3,977,022 B**；无链接或遍历错误。
六个声明外域的存在性和 metadata entries 完全相同，不扩张为全系统无写声明。

原 seal SHA `89c19c9c6b745f41eed7042064515cbd7d4b176f063408235c2dab5df5c9f144`，
输入/资源/静默检查通过。root 从原 seal 完成工具结果保留的 post-fsync 观察为
**1148.5123171668965 秒**、outer exit **2**、`partial_or_fail`，带 session 45561 /
chunk 787626 来源；C2 独立核对磁盘字节、seal、其报告标量和来源，未重跑 seal。
`selected_probe_ok=false` 描述缺失的 reload → import → probe 完整选择链，
不能据此否定已独立通过的 P2 能力阶段。

审查器第一次检查误把普通 LogPython PASS 标记要求在 console；检查两份原日志后，
定位其在 abslog `p2/ue.log`，console 实际记录 commandlet successful。修正审查器
读取对应原日志后成功，不改应用源码或原始证据，不放宽正常退出或能力验收。

下一步：新审定的有界 import/reload 迭代，以 `877696e` 和保留的 P2 能力原件为
明确输入，提前完成准备与准确卡审查；旧 I22 root 保持封存。本轮不授真实资产保存、
运行时或画质门。审查文件由 root 读报告及 scoped 摘取作为等效独立证据门集成；
本审查树先保留，待主任务确认集成与运行依赖后再按工作流清理。
