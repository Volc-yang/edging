# I22-A：能力先检与导入修正

2026-11-10；实现基线 `cd3b26fde5655b77482daa051eb2eb00c2c55359`，复用原树/分支 `codex/i21-import` 与草稿 PR130。只读参照 root 的 `doc/design/universe-i22-import-correction-plan.md`（C0 SHA `0ebce94464c98becd8297833ab574b698dc9118363f5fedaafd9297761cb6f24`、context commit `d194b4b`）；未将 root 未合并上下文假定为本树源码。

状态：**部分完成：p2真实Native能力probe通过；实际I20资产导入/保存、新进程reload及视觉未验收**。实际执行源码为 `877696e7ef61a2fbfbc50fb0cd88ba10ceacb644`。本 agent 不启动UE、不写DevSSD、不读owner/key；运行由root执行，I21和p1全部证据/失败原件不改。root/C2接受部分结算，不集成导入源；本次仅本地文档commit，不push/更新PR/merge/cleanup，工作树保留。

## 源实现

`ue_entry.py` 公开显式激活 AssetTools、MaterialEditor、InterchangeEngine/Import/Pipelines、EditorScriptingUtilities、StaticMeshEditor。load_module 成功也返回None，未用返回值判断成功；后续真实实例/调用裁决。StaticMeshEditor 的 AdvancedPreviewScene、EditorSubsystem 安装 dylib 纳入preflight pin。

`probe.py` 使用实际安装 Cube/DefaultTexture，以公开 SystemLibrary.duplicate_object 克隆到 find_package('/Engine/Transient')，创建具体 transient Material/AssetImportData；不实例化抽象Object，不保存或外部导入。真实调用mesh/section/slot/LOD/collision/bounds/Nanite、纹理尺寸/flags、材质连接/通道/断Alpha/恢复、pipeline/stack setter-getter。void setters只用实际getter判定。Cube自带碰撞只检查getter有效并toggle/restore，真实导入仍严格collision0。原fixture包SHA和项目Content保持原样是独立检查项，不能由声明代替root退出后检查。

pipeline 用 native bCollision bool set/get；另读 native Collision fallback enum，拒绝错误类型。显式 bBuildNanite=false。Native source-model LOD数量与render LOD数量、render vertices、editor UV/render texcoords分字段；source_expected_triangles/native_render_lod0_triangles/native_nanite_input_triangles 分账，真实 imported Nanite必须disabled/input0，源三角/AABB匹配不放宽。I20 Alpha/PBR/GL与DX覆盖、地表球禁用保持。

import/reload每个进程独立运行同套本地capability检查，不能沿用另一个进程的subsystem。import前还消费独立SHA固定的真实probe原件，与probe job、recipe/index和共享源码snapshot逐项匹配。mode/pid/job_sha256/recipe_sha256/source_index_sha256/source_scripts 在有有效job的正/负结果保留；import输出consumed_probe_ref供root和card交叉复核。

## Root 精确准备接口

README列出所有命令。可在首clock前准备 `probe --attempt 1` 与 `import --attempt 1 --probe-attempt 1`；后者静态dispatch不能运行。root独立接受真实probe execution/postwrite/Native门后，调用 `bind-import --attempt 1 --probe-sha <实际接受SHA>`，排他生成dispatch-bound.json并注入 I22_PROBE_RESULT_SHA256，保留原dispatch。绑定只是字节/合同检查，**不授root执行/normal/quiet/预算/C1接受**。

新root为 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import`；p1/p2、a1/a2独占Host/Content/user/log/DDC/tmp；reload晚绑定已成功import结果SHA，打开同一保存Host/Content，禁止重导/保存。明确argv list/shell=False、I22_IMPORT_JOB_SHA256独立pin、UE_SKIP_UBT_SDK_SETUP=1、NoTrace/Isolated DDC/NoDefaultGraph。root执掌max2×90s probe、max2×240s import、1×180s reload；1200s/4GiB/真正host Content512MiB，DDC/Content另列缓存仍计总量。旧I21不存在被清零/补回的门。

## 实际 CPU 结果

- `python3 -B -m unittest tests.test_realism_import -v`：6项通过，包含原5项边界及新增synthetic JSON probe绑定/错job、错mode、错源码、不完整实际证据拒绝。没有unreal mock/stub；CPU正例不授Native。
- AST解析全部Python成功，未import/执行UE producer。
- `prepare.py preflight` 实际只读通过：20源、25相关安装模块、2安装fixture文件、698安装Python文件及44启用plugin闭包，全部无用户startup/pip新增要求；Foundation真实Documents检查通过。最终 `preflight-counts-final.json` SHA `5deb02466dd54caae3db0dc29193d1f756ebb562b0bb5f6ea8ca36a723a3f08f`，snapshot_sources与源字节一致。
- recipe SHA `f228bf56097d096fd85a20e8801ed7edbec29d84a4047ac577b8812351951270`。早期preflight原件保留为当时源身份，不授权最终版本。

以下CPU记录保留各自源身份，不替代后述p2实际结果。仍未验证：保存I20组合5/14/3包、实际导入资产的Native正/负例与新进程reload。能力fixture通过不授这些门。Metal、法线外观、runtime profile/HUD、地形/世界/Genesis继续后置。

## C1 窄修与当前源身份

独立审查和owner自查共同确认 Python FName别名大小写不敏感：raw `Collision` 可能被解析为bool `bCollision` 的Python别名。因此枚举现在只用公开ScriptName的Python名 `fallback_collision_type`，bool继续精确 `bCollision`，不是轮询不同名字的fallback。

probe外层在进入修改前登记三份texture clone初始实际flags/尺寸/身份；COLOR/MASKS/NORMAL配置保持到材质recompile、Alpha断开/恢复及pipeline调用结束，之后恢复各clone初值并逐项读回。错误路径也恢复；877696e按compression→SRGB→flip顺序并保留主异常及全部before/after/diff。原Engine Cube和Texture的完整实际getter/身份快照前后相等与包文件SHA分别验证；不会调用要求I20来源的texture_metadata去假验Engine fixture。import消费gate同样要求clone恢复与Engine原对象不变证据。

受影响JSON绑定CPU检查通过，全部AST成功。最终只读 `preflight-c1-complete.json` SHA `c39bf1c78effa1622ed03d7f218911685cde2b5128db7ebc23d6a2d7833a0004` 为ready，snapshot源逐字节匹配。其余preflight保留各自当时身份，不授权新源。无UE/DevSSD/发布操作。

## Root/C2 实际部分结算

- p1恢复失败原件保留，不由p2覆盖。p2以源码877696e实际执行，PID86365、parent wait0、非强制、后代静默；Native result SHA `1a88df030a7619b34d68ca2210183c1502f336401505333d8bc1301822b38676`。三份texture均128×128，全部严格恢复、diff为空；原fixture实际getter及包不变。公开模块激活、完整能力调用与临时对象修改/恢复门通过。
- import未派发：准确新卡准备完成时只余130.865s，低于所需120+30s，root判NO-GO，没有放宽预算或追加尝试。a2仅静态绑定成功p2，既无Native import result，也无Host Content文件；reload skipped。绑定存在或probe PASS不能称已保存I20资产。
- 最终封存原件摘要前缀 `89c19c9c`（完整值见root封存索引）；post-fsync连续耗时1148.512s，新root逻辑文件27,805,158字节，I20全部34个持久文件不变、六个声明外域增量0，最终静默。root与C2接受上述有限能力门及部分结算，实际导入源不集成。

Act：保留本工作树/分支、I21/I22全部原件与实际源码877696e；下一迭代从已通过能力与同源成功probe身份出发，重新审定独立新预算/导入及reload卡，实际保存并验收I20组合。公开发布仍停止，本次只提交该状态文档。
