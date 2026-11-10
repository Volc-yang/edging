# I20-A 交付与复查

2026-11-10；状态：**文件取得/owner 自检 complete，独立审查与集成 pending**。工作树 `/Users/yangacan/edgeWorld/edge-world/.worktrees/i20-assets`；分支 `codex/i20-assets`；基线 `6c533afb537a9c45bd471eb83887cdcd87b42052`；PR 目标 `codex/plan-consolidation`。只拥有 `doc/design/universe-i20-asset-profile.md` 和本证据目录；实际大文件全部留在 DevSSD，不进入 Git。

## 结果及证据身份

| 门 | 实际结果 | 证据 |
| --- | --- | --- |
| 许可与固定来源 | pass；Poly Haven 下载资产 CC0；未下载或执行第三方代码 | `metadata/` 原始 API；`metadata-receipt.json`；`CC0-1.0.txt`；许可 HTML 原件在 DevSSD |
| 下载前完整清单 | pass；3 个 2K glTF + 全部 include + 明确补充材质贴图，共 20 文件 | `acquisition-plan.json` SHA `eaa2ee7fe45baf7b54222e5ad5d5df7962633f0b69dedee34b9ef98c1b7903d9` |
| 实际文件/摘要 | pass；41,949,796 资产字节，逐文件源 MD5 与本地 SHA-256 匹配 | `acquisition-receipt.json` SHA `9adfbad141c8ec2a9034ae02dfc88badbb0f3401fd039587104dbbccf28cdddc`；`asset-index.json` |
| 限额 | pass；实际响应体 42,116,535 字节；最终 34 文件；网络阶段 145.219 秒；所有请求各小于 60 秒 | `metadata-ledger.json`、`binary-ledger.json`；相同持久 monotonic 起点，无重试 |
| 依赖/格式/范围 | pass；glTF2.0，无 required extensions；buffer/image 引用均为本地、闭包存在；几何可访问，索引不越界；14 张贴图均 2048² | `verification.json`；只检查格式头和结构，不冒称完整图片解码或 glTF 官方 validator |
| 有效拒绝 | pass；缺首个必需文件、复制后损坏首个 BIN、`../escape` 三项均被拒绝 | `negative-checks.json`；临时合成负例，原资产未更改 |
| UE class/slot/import/build | planned，未运行 | D3 后续验收 |
| 写实画质 / Metal / 性能 / 只读画面 | planned，未运行 | D4 后续验收 |

下载请求 UTC 从 `2026-11-10T03:56:49` 附近开始；精确响应记录及结算 UTC 见 ledger。没有失败、重试或临时提高限额。二进制阶段复用元数据阶段的起点与字节账，不重新计时清零。`binary-ledger.file_count=32` 是保存最后两个账/收据前的采样；最终 read-only verifier 记录 34，未以中途数量冒充最终数量。

## 文件布局与复查

实际根：`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets/`。`assets/<asset>/` 保持 glTF 原始相对引用，`metadata/` 保存 API 与许可原始响应，根部保存不可覆盖的固定清单/账/收据。网站许可 HTML 原件不复制进 Git；其内容身份由 metadata receipt 固定。所有下载内容均作为数据处理，未运行脚本、安装插件或启动 UE/worker/Genesis。

本目录的 `acquire-metadata-snapshot.py` 逐字节匹配 metadata receipt 记录的 helper SHA；`acquire.py` 逐字节匹配 binary attempt/receipt 的 helper SHA。后者增加 plan/download 子命令，保留前阶段身份。**原 metadata receipt 中的旧绝对 helper 路径现在指向已演化脚本，直接读取该路径不再匹配旧 SHA**；原 receipt 没有改写。须使用 [phased-source-provenance.json](phased-source-provenance.json) 将各阶段旧记录映射到保存的实际源字节、稳定仓库路径和不可变 Git blob；[provenance-check.json](provenance-check.json) 逐项核对旧 receipt SHA、保存字节与 `a979027` Git blob 相同。实际资产输入索引也固定到该提交的 blob 与 DevSSD root，不依赖待清理 worktree。

脚本专用于本轮独占 root；再次运行获取命令会因已存在文件/attempt 而拒绝，不能用重跑覆盖本轮证据。后续使用稳定仓库路径或 Git blob 复查 helper，不应在 cleanup 后尝试恢复旧 worktree 路径；未来原生 UE profile/派生资产身份仍须在 D3 冻结。

无需网络的实际复查命令（在本工作树）：

```sh
python3 -B doc/evidence/universe-I20A/verify.py /Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets
```

输出包括来源匹配、资源计量、全部模型/材质/节点、实际三角形计数及每 primitive 源 AABB。依赖仍在 DevSSD，保留此目录；工作树本身可在 PR 审查/集成后按统筹流程清理，不是 UE 运行输入。

## 限制及下一步

已发现 fern glTF 的 Mask 引用 JPEG 不含透明通道；已取得独立 Alpha PNG，未来 UE owner 必须显式接线。地表 glTF 是材质预览球，不能作为世界地形。文件源版本和几何范围通过不等同于 UE 材质、导入轴/slot、pivot、画质或物理通过。此组合无完整树冠/水体/生态，未清除既有画质缺口，也未导入来源不明的 Dot 分支。

下一 owner 从固定 `asset-index.json` SHA 接入 B 的版本化只读呈现契约，执行 D3 导入/真实 UE metadata 固定，再用 D4 原生 Metal 图像与只读/原子切片证据裁决。主任务负责独立审查和合并；本 agent 不合并、不清理未集成 worktree。
