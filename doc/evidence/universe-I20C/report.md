# I20C 独立审查

2026-11-10。父节点 I20；独立审查 owner `/root/i20_review`。基线 `6c533afb537a9c45bd471eb83887cdcd87b42052`，分支 `codex/i20-review`，工作树 `/Users/yangacan/edgeWorld/edge-world/.worktrees/i20-review`；仅修改本证据目录。父任务负责 PR、CI、集成、实际运行与清理。

## 范围和方案门

[方案审查](plan-review.json)接受首轮 A 有界许可资产输入、B 独立呈现契约/合成 CPU 检查、C 独立与跨输入审查。D3 真实导入/适配/编译、D4 Metal 画面/输入/退出/写实评价仍是后续任务。本 reviewer 未启动 UE、worker、Genesis、GPU 或 UI，没有读取 owner/key 内容、下载依赖或改旧 authority/parser/I0A；没有联系 Dot，也没有把其他 Codex 对话当作 Dot。

## A：接受实际来源、许可、文件与闭包门

审查最终提交 `30907e8dd645cb1b7c3580cf101f180b77b47865`，相对基线 23 个 A 所有文件；`git diff --check` 通过。独立结果：[a-independent-review.json](a-independent-review.json)，owner verifier 实际重跑：[a-owner-verifier-rerun.json](a-owner-verifier-rerun.json)。

- 逐字节重读 28 个保留响应体，重算 size、MD5、SHA256：合计 **42,116,535 B**；均 200，无 redirect/partial/retry。元数据到二进制沿用同一 monotonic 起点，145.218854 秒，最长单请求 2.410143 秒，低于固定 256 MiB/20 分钟/60 秒上限。
- 固定 plan 的 20 个实际 payload 全部与源 MD5、receipt SHA/size 一致，**41,949,796 B**；无跟随符号链接的实际树枚举 34 文件、0 walk/stat 错误，低于 64。中途 ledger 的 32 不是最终数量。
- 原始 Poly Haven 官方许可 HTML 明示模型/纹理/HDRI 为 CC0，保留法律文本逐字节一致。该结论仅覆盖这些来源资产，不推定其他模板代码或商店内容许可。
- 原 metadata receipt 的旧 helper 绝对路径已指向演化脚本，不能直接按旧 SHA 复查。新增 typed phase 映射正确保留旧 receipt；独立重算保存源、`a979027` 不可变 Git blob、原 receipt 均一致。metadata snapshot SHA `a51fa23d…74087`、binary source SHA `4582ccc7…fa822b`。binary receipt 原本固定 helper SHA；绝对路径由阶段映射补充。稳定 index SHA `d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7` 及 DevSSD root 与映射一致。
- 真实 glTF/BIN/图片闭包、accessor/buffer/索引范围 owner verifier 通过；独立临时副本的缺 BIN、损坏 BIN、符号链接 BIN、`../escape` 四负例均拒绝，未改变真实源文件。
- 另用已有项目 Pillow 完整 CPU 解码 14 张真实图片，全部 2048²。蕨叶 BaseColor 是 RGB JPEG、没有 alpha；独立灰度 Alpha PNG 范围实际变化。该额外检查仍不证明 UE 材质、采样、法线或画质。

保留实际缺口：fern glTF MASK/0.5/TwoSided 并不使 RGB JPEG 自动透明；D3 必须连接独立灰度 mask。所有原 glTF 仍引用 GL 法线，额外 DX 输入只能显式 recipe override。地表模型为材质预览球，不能作为地形；真实导入 class/slots/pivot/轴/尺寸/package hash、物理与画质均未验收。

## B：CPU 契约审查与最小返工

先审查 `e25d82649da34aadb3009414bad8e002c291119c`：13 个 B 所有文档/fixture/检查文件，未改产品或 authority。独立运行原 14 项全部通过，实际输出保留在 [b-before-finite-fix-owner-checks.txt](b-before-finite-fix-owner-checks.txt)。额外 State/Event 跨切片不匹配及 Native slot 声明不匹配均拒绝；有限 Native 形状合成提案仍明确 authenticity=false。

但有效 JSON 数字 `1e999` 被 Python 解析为 infinity，原 `parse_constant` 不能捕获；带无穷 units/pivot/bounds 的合成 Native 提案被错误接受为一致。已请求 B owner 最小修复和定向回归。原失败、精确合成字节及源摘要永久保留：[b-before-finite-fix-independent-review.json](b-before-finite-fix-independent-review.json)、[overflow 输入](b-before-finite-fix-overflow-synthetic.json)。这不是实际 Native/UE 运行或越权写入。

最终修复提交 `d6fe60de9c3ad9fad837841f2bd3bfb027a90896`：独立审查有限 float 解析与 schema/API 字典递归 guard，仅对 float 调用 `math.isfinite`，保留精确整数语义。实际重跑 **15 项 / 0.496 秒 / exit 0**，另 5 项独立定向检查全部通过，原精确 `1e999` 复现输入现被拒绝。owner 的最终原始输出、checker/fixture 的 byte/SHA 清单也经独立重算一致；结构 schema 和 fixture 字节未改变。

因此 **接受 B 的设计/合成 CPU 合同门**，不授予 Native/import/平台/材质/原子 HUD/画质门。最终独立证据：[b-final-finite-fix-independent-review.json](b-final-finite-fix-independent-review.json)、[实际 15 项输出](b-final-finite-fix-owner-checks.txt)；原失败按原身份保留。

## 跨输入与后续门

A 的真实 index 与 B 文档同一 SHA。B 正例全部是 `.fixture` 字符串和 unresolved metadata；其 fern/rock/ground 角色声明不是已经导入的 Poly Haven 资产。B 明确原六个 Cube 是场所 marker，不是植物物种；使用稳定 place/binding/instance 身份，并单列 BasicShapes 权威 projection 与新只读 presentation mode。未静默重写旧版本。

ViewBinding 同时保存 world/Manifest/State/Event、tick/revision/watermark、Transform、profile SHA、独立 renderer SHA、generation；D3 同一 owner 必须修复目前 Session 先于 ApplyVerified 更新的 HUD/场景混片风险，验证真实 Actor 与已呈现 HUD 的同次提交。schema/CPU 合同匹配不能证明实际原子性。

后续 D3 必须固定真实 source/import/package 依赖、单位/轴/pivot/bounds、slot、PBR 通道及 GL→显式 DX override，生成真实 Native evidence，完成隐藏装配和失败保留旧完整视图。D4 再按独立固定画质阈值、Mac/Metal 和新预算采原生 PNG、只读动作、正常退出与性能证据。写实质量、平台支持、权限状态不变以及玩家体验门均为 **planned/not run**；I18 exact3 的有限接受与 I19 失败不变。

## 重现入口

在已集成仓库使用稳定相对路径；大文件留在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets`，不依赖待清理的 A/B/C 临时 worktree。只读 reviewer 脚本接受显式 repo/root/output 路径，输出应使用新的证据目录或 attempt，保留已有失败。

```sh
/Users/yangacan/edgeWorld/edge-world/.venv/bin/python -B doc/evidence/universe-I20C/review_assets.py <integrated-repo> /Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets <new-review-output-directory>
/private/tmp/edgeworld-i20b-contract-env/bin/python -B doc/evidence/universe-I20C/review_contract.py <integrated-repo> <new-review-output-directory> <new-attempt-id>
```

环境与库版本见 [review-environment.json](review-environment.json)。本 reviewer 只裁决方案/输入/合成检查；父任务仍须独立检查最终集成文件和 CI，再记录 D3/D4 派工与 worktree 安全清理。
