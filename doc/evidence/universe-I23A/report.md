# I23-A：PR130 文件映射拒绝缺口修复

基线 `768b1ac4a608bd4a3b6eed39001117e1b8f2692b`，复用 `codex/i21-import` / 原worktree。只读执行计划为root的 `doc/design/pr130-merge-validation-plan.md`，C0 SHA `06b3b2feae549e177b8c5f7347dbf595b04567def38a4df58d5e21f6a478b0b0`。实际测试源码为 `df1863e900ad7b96c36dc05507ac221d6ab5ab25`。状态：**代码修复、9项CPU和root完整Native执行通过；独立C2、父级最终复核、最终head CI及合并仍由root处理**。尚未将执行通过冒称已审查接受或已合并。

最小改动：`common.file_map()` 用scandir/lstat显式遍历，任何枚举、stat、open或read错误直接传播；只接受真实目录及普通文件，链接/FIFO/socket/device拒绝。必需根不存在时抛FileNotFoundError，非目录根拒绝，存在的空目录仍返回空映射。普通文件维持原相对路径/实际字节数/SHA结构。打开使用NOFOLLOW/NONBLOCK并核fstat普通文件及dev/inode，避免lstat后替换成链接或FIFO时跟随/阻塞。

固定OUTPUT仅改到 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import`；README和路径断言同步。保留I22协议字段、环境pin、`/Game/EdgeWorldRealism/I22`包路径及严格Source/Alpha/PBR/GL-DX/Nanite/几何要求。其他producer不改，I21/I22封存原件不动。

实际检查：`python3 -B -m unittest tests.test_realism_import -v` 共9项通过（`cpu-check-final.txt`），覆盖普通嵌套文件、有效空目录、缺失根/非目录根、实际链接/FIFO，以及枚举/stat/open/stream-read失败不返回部分成功。sandbox拒绝创建AF_UNIX测试socket的初次原件保留于 `cpu-check.txt`；最终socket/device类型仅注入stdlib lstat结果检查拒绝分支，明确不是实际Unixsocket创建成功。没有unreal mock/stub；这些CPU检查与下述root真实Native执行分开计。全部Python AST和git diff检查通过；本agent没有运行UE、写DevSSD、读owner/key、push或merge。

## Root实际运行原件

原始结果、日志、监督与完整摘要留在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import`；下表结果摘要为root提供的前缀，完整值由该次封存索引固定。

| 阶段 | 实际身份 | 实际结果 |
| --- | --- | --- |
| capability probe | PID87036；result SHA前缀 `971c6fb` | 真实能力检查通过 |
| import | PID96593；result SHA前缀 `e2af513` | 5 StaticMesh / 14 Texture2D / 3 Material，实际保存22包，共39,910,827字节；真实Alpha断开/slot错绑负例准确拒绝，恢复通过 |
| 全新进程reload | PID11448；result SHA前缀 `fb7cd5fb` | 完整Native快照与import相等，Content文件字节前后不变 |

三次actual parent wait均0、非强制、后代静默。最终seal SHA `cf2cf5e3725376ad64f1d7480d2139a92a94e6229ad717863a0f50fb99e51bb8`；post-fsync连续492.531216541秒，新root逻辑文件77,341,675字节，真正Host Content39,910,827字节，DDC13,293,053字节单列且计入总量。该结果只覆盖本轮导入/Native回读，不授Metal画质、runtime adapter/HUD、地形或世界/Genesis门。

下一步：新PR审查会话完成独立C2，root完成父级回放复核、推准确最终head运行CI并更新PR130。必需门和准确head CI均通过后才按用户既有授权合并；本agent不发布、不集成、不清理工作树。此次仅文档状态提交，实际测试源码df1863e不变。
