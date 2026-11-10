# PR130：审查、补证与合并

2026-11-10。用户最新指令：增加 Pull Requests 审查会话并执行 PR 合并。
当前唯一 open PR 为 #130，head `768b1ac`，远端 target
`codex/plan-consolidation@5f2bbe3`；统筹本地 `1a1d64a` 另有已发布回执。
独立审查会话 `01a1c4c5-5809-79c2-ae72-2fa4b70ee845`。
本计划待该会话 C0 接受；不把合并授权解释为缺失验收已经通过。

## 任务树与边界

1. **C / 新 PR 会话，只读审查。**核对准确 ref、diff、CI、契约与原件。
   已发现 `common.file_map()` 忽略 FIFO 等非普通项的可复现缺口；最终问题清单以
   独立报告为准。C0 先审本方案，C1 再审准确源码及执行卡，C2 审真实原件。
2. **A / 现有 i21-import worktree，base 768b1ac。**接受 C0 后仅修复明确问题：
   将 file_map 改为遍历遇错即失败，拒绝链接和非普通文件，保持目录和有效文件
   的原有映射；添加相应边界回归检查。为保护已封存 I22，将固定输出根改到
   `I23-20261110-import`，同步路径断言/使用说明。保留 I22 协议字段与
   `/Game/EdgeWorldRealism/I22` 包路径，避免无关接口变化。
   写范围仅 `scripts/realism_import/`、`tests/test_realism_import.py`、
   `doc/evidence/universe-I23A/`；不扩大通用框架、不改源资产/容差/引擎源码。
3. **R / 统筹，唯一 UE 执行者。**新证据 `doc/evidence/universe-I23R/`。
   复用已审 I22 工具的副本，只版本化新根及本次必要绑定，旧 I22 工具/卡/原件
   不改。全部静态输入、前检、probe/import 卡模板和独立审查在连续时钟前完成；
   实际结果 SHA、reload 包与成功链仅按已审模板晚绑定。
4. **C2 → root → GitHub。**全部必需门通过后，独立 C2 与父级核查、准确 head CI
   通过，更新 PR 范围/验证事实，移出 draft，并以 expected head SHA 合并到
   `codex/plan-consolidation`。不合入 main/feature，不改主工作区用户内容。

## 真实验证与停止条件

新根 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import`。
固定 UE 5.8.3 CL58210709、I20 index `d9df98db…0447b7` 和所有原素材不变。
先真实能力 probe，再真实 5 StaticMesh / 14 Texture2D / 3 Material 导入/保存、
Native metadata 与 Alpha/slot 故障注入恢复，最后在全新进程 reload 完整快照。
依赖失败则不派后续阶段；失败原件保留，不把未执行标为通过。

沿 I22 卡：从首 probe 到最终 fsync 连续 ≤1200 秒；新根逻辑文件 ≤4GiB，
实际项目 Content 合计 ≤512MiB，DDC 单列且计总量。至多 2 probe（各≤90秒）、
2 import（各≤240秒）、1 reload（≤180秒）；余量不足即 NO-GO，不重置时钟。
NullRHI/unattended/NoTrace/独占 FileSystem DDC/清环境/真实父 wait/精确进程
静默/六声明外域/终输入 hash 和只读 reload 文件图要求保持。
Native 失败只返工受影响路径并须 C1 接受；不改 fixture、三角数或 AABB 容差。

## 合并判定

file-map 缺口与其他明确代码问题解决、准确源码 CPU/CI 通过；真实能力、5/14/3
保存、Native 正/负例恢复、独立 reload、文件/输入/资源/正常退出、独立 C2
与父级复核均通过，才授 D3-IMPORT 并合并。Metal/运行时画质仍为后续单独门。
若不能满足，记录精确阻塞与已完成部分，PR 保持 draft，禁止伪造批准或强行合并。
用户已有合并授权，不重复询问一般合并权限。

## 上下文与保留

统筹更新 PR 审查登记、I23 证据与 backlog，按范围 commit。公开修复/审查仅服务
于用户已要求的同一 PR 审查合并；原始 UE/PS 日志及资产二进制留在 DevSSD。
所有旧失败、主 checkout、I15 构建、I12B 恢复与源工作树依赖保留；只有干净、
已集成且运行依赖已落到稳定路径的任务树才可 non-force 清理。
