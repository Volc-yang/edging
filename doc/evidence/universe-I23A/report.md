# I23-A：PR130 文件映射拒绝缺口修复

基线 `768b1ac4a608bd4a3b6eed39001117e1b8f2692b`，复用 `codex/i21-import` / 原worktree。只读执行计划为root的 `doc/design/pr130-merge-validation-plan.md`，C0 SHA `06b3b2feae549e177b8c5f7347dbf595b04567def38a4df58d5e21f6a478b0b0`。状态：本地代码/CPU交付；真实5/14/3保存、Native负例与reload由root后续执行，本任务不授这些门。

最小改动：`common.file_map()` 用scandir/lstat显式遍历，任何枚举、stat、open或read错误直接传播；只接受真实目录及普通文件，链接/FIFO/socket/device拒绝。必需根不存在时抛FileNotFoundError，非目录根拒绝，存在的空目录仍返回空映射。普通文件维持原相对路径/实际字节数/SHA结构。打开使用NOFOLLOW/NONBLOCK并核fstat普通文件及dev/inode，避免lstat后替换成链接或FIFO时跟随/阻塞。

固定OUTPUT仅改到 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import`；README和路径断言同步。保留I22协议字段、环境pin、`/Game/EdgeWorldRealism/I22`包路径及严格Source/Alpha/PBR/GL-DX/Nanite/几何要求。其他producer不改，I21/I22封存原件不动。

实际检查：`python3 -B -m unittest tests.test_realism_import -v` 共9项通过（`cpu-check-final.txt`），覆盖普通嵌套文件、有效空目录、缺失根/非目录根、实际链接/FIFO，以及枚举/stat/open/stream-read失败不返回部分成功。sandbox拒绝创建AF_UNIX测试socket的初次原件保留于 `cpu-check.txt`；最终socket/device类型仅注入stdlib lstat结果检查拒绝分支，明确不是实际Unixsocket创建成功。没有unreal mock/stub或Native成功声明。全部Python AST和git diff检查通过，无UE、DevSSD写、owner/key读取、push或merge。

下一步：独立C1审准确源码与I23监督卡；root在新预算中实际probe→5/14/3保存/Native负例→新进程只读reload→独立C2和父级复核。必需门和准确head CI均通过后才按用户既有授权合并PR130；本agent不发布、不集成、不清理工作树。
