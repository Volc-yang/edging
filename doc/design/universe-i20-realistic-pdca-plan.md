# I20 PDCA：写实呈现输入与改造计划

2026-11-10；parent=Dot写实世界需求；统筹root；基线`e76f4b6`，集成分支`codex/plan-consolidation`。状态：**方案经独立审查/root接受，可派发A/B，尚未派发UE/呈现实现**。用户要求开始PDCA开发测试，先按新需求调整计划；另明确允许开源模板，并授权直接向Dot询问候选代码位置。用户已清除旧goal，本轮不用goal状态承载进度。

## P：本轮有界目标与已知约束

把“真实世界、不要卡通、优先3A模板参考”变成可复现的资产输入、版本化Universe只读呈现契约与可执行测试卡。首轮落地开放许可的小型自然资产组合，解决原样区和新版Universe的真实接口缺口；不以CPU检查/下载成功宣称写实画质通过。

已观察：本地尚无可直接导入的完整自然资产组合；Electric Dreams官方要求DX12，保留为视觉参考。开源仓库许可证与配套美术许可分开核对，不把免费或可下载称为开源。优先使用独立CC0模型/扫描材质配合现有UE发布版骨架；无购买、EULA接受或整包搬运。

SDK实际观察：已安装UE5.8.3 CL58210709；当前`xcode-select`为`/Applications/Xcode.app/Contents/Developer`，`xcodebuild -version`为27.2/27B52。安装内Apple_SDK.json声明15.2.0–27.9.0，27.2在其范围内，但**尚未进行本轮编译**；不能把未固定版本的网页表格或旧成功构建升级为新构建结果。引擎源码不改。

Universe v0.2的authority/parser/worker audit严格固定BasicShapes技术资产和`basicshapes-proxy.v0.2`。六类场所装饰是Cube marker，没有树种/地表/水面角色。新版写实呈现应增加独立显式opt-in的本地profile及启动SHA pin，消费已验证O，保留原权威资产清单和旧验证器。不能把`asset-cube`统一替成树，也不能从颜色/帧数创造权威实体。profile引入必须保留单writer、历史绑定与Genesis形状/尺寸，不推进逻辑时间。

## 方案树与本轮边界

```text
P0 root计划与独立审查
 ├─ D0 Dot交付询问/身份核对（待可寻址入口；不阻塞独立准备）
 ├─ A 开放许可资产profile/限额取得与校验 ─┐
 └─ B Universe只读profile/原子ViewBinding契约与固定测试卡 ─┤
                                      C root输入交叉核对+独立复核
                                      Act精简上下文/commit/下一轮实现输入
后续：D3具体呈现代码/UE编译 → D4真实Metal视觉/只读/退出与新响应Native验收
```

I20本轮完成条件为A/B/C三个有界交付通过；D3/D4必须显式另卡，在资产身份/接口冻结后执行，不能在本轮偷偷引入未审查加载器或运行UE。这样一次PDCA有确定终点，资产和契约不会在活跃运行窗口中临时研究。D0未取到候选时继续标记未交付，不重写或冒称已合入Dot补丁。运行正确性、视觉、平台/编译、性能是独立门，旧I18/I19及所有失败保持。

## 叶任务P/D/C/A卡

| ID / owner / 排他路径 | Plan与Do | Check与证据 | Act |
| --- | --- | --- | --- |
| D0 / root | 通过已授权且可寻址的Dot消息入口询问repo/branch/base/commit/diff、592项检查原件、资产清单与Universe适配范围。当前工具目录没有Dot消息API，聊天清单未列出Dot/Edge；询问尚未发出，不把其他Codex会话冒充Dot | 交付身份必须可只读取得并和声明相符；记录请求草稿及未发送原因，不依赖截图猜提交 | 待交接；候选到达后只做差异审查，保留已完成A/B，不重复劳动 |
| A / asset subagent；`doc/design/universe-i20-asset-profile.md`、`doc/evidence/universe-I20A/`，大文件仅新独占DevSSD资产目录 | 固定PolyHaven fern_02、boulder_01及forrest_ground_01的可用低分辨率版本；优先完整模型+2K或更小PBR，先查API体积/依赖，再取得具体文件；松树大包延期。候选20m×20m仅为lookdev fixture，不是新权威世界或森林完成 | 来源/许可、实际文件size/SHA256及源校验值、全部依赖闭包、路径安全、缺文件报错；真实文件校验与预览图区分。无实际文件则不通过资产门 | 接受具体输入组合或只重开缺失资产；不退回代理宣称写实。导入、Mac材质效果仍planned |
| B / Universe subagent；`doc/design/universe-realistic-presentation-profile.md`、`doc/fixtures/universe_realistic_presentation_profile_v0_1/`、`doc/evidence/universe-I20B/` | 冻结独立本地profile/启动信任、资源依赖和角色/slot/单位/pivot、场所+稳定实例映射、旧authority与新view的独立provenance。定义ViewBinding绑定Manifest/State/Event/triple/Transform/profileSHA。整组加载成功才提交画面与HUD；失败保留上一完整切片且显错 | 固定schema与合成正/负例，实际验证格式/引用/角色/时间绑定/错profile等拒绝；测试卡覆盖真实UE class/slot/hash、缺资产/迟到加载、历史与全map不变。代码/真实图尚未运行须明确 | 独立设计接受后再生成D3实现卡；不修改旧parser/golden/worker/authority/I0A或现有GameMode |
| C / root + independent reviewer | 核A实际文件和B接口/测试卡是否能由下一owner执行；版本化关联，避免依赖临时任务树 | 实际复核文件身份、许可/平台来源、正负例结果、互不冲突的owned paths、合入状态；无需为纯文档重复全CI | accept/rework具体叶；只承诺已测范围，更新上下文并有据清理临时树 |

B需明确已有风险：GameMode当前在`ApplyVerified`前更新Session.Observation/bHistory，加载失败时可能新HUD/旧画面。后续D3同一owner必须原子提交已呈现ViewBinding，或分离已收到/已呈现观察，不能仅证明authority map不变。

## 资源与停止条件

- A的原始资产写入`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets/`新独占目录；不放入旧I15计量root，不删除任何旧输出。源payload上限256MiB，最多64文件；网络阶段20分钟上限、每文件60秒，先核完整下载清单再取文件。超预算则在下载前缩为蕨类+地表或标部分；禁止开始后隐瞒/提高限额、反复重试挑结果。源许可/格式/路径不符立即停对应资产。
- 限额按实际流式读取的所有body/partial文件执行，不能只相信API或Content-Length；redirect/依赖URL逐跳核可信HTTPS域，拒绝路径逃逸和指向本机/其他私域。失败原件计入资源，先保存失败再结算。
- A不运行下载内容、安装插件、执行第三方脚本或导入UE；大文件不上Git，只提交来源/版本/摘要/许可与配方。B不打开UE、worker、Genesis、owner/key，不更改产品或历史状态。root与reviewer也不在本轮使用GPU。
- B schema/合成数据只是独立设计与格式检查，不是渲染、物理、加载器或新Native正确性通过。A取得CC0资产不是其导入/画质通过。
- B把结构检查和语义检查分开报告：文件SHA实际匹配、依赖图闭包/环、跨字段关系只能由小型独立contract检查或后续明确测试证明；HUD/画面原子性须真实D3 producer验证，不能由schema正负例伪证。允许在证据目录使用小型有界CPU合同检查，不增加产品框架。
- 所有写任务在审定计划提交的独立worktree/分支，目标`codex/plan-consolidation`；A与B可并行，各自PR/审查/实际checks后集成。主checkout未提交改动不碰。

## 后续D3/D4最小验收轮廓

固定真实观察+profile；材质和完整模型全部存在，无卡通兜底。输出绑定含真正已呈现的triple及profileSHA。验证当前→历史→当前、缺资产/错slot/迟到资源时HUD与画面不混切片、UE不模拟Genesis物理。精确提交的官方UE编译与真实Metal原PNG/正常退出分别验收；正式视觉参考、有效像素和性能阈值在运行前冻结。直接TTY+stdin握手、NoTrace/独占DDC、完整写域/资源上限沿既有可靠规则重新备卡；本轮不复用过期I19卡或扩大I18 exact3。

## 独立审查来源

`/root/i20_review`只读检查计划、workflow/backlog及安装内SDK范围后接受A/B/C首轮；root采纳实际字节/redirect限额和结构/语义分账两条执行澄清。该审查未运行UE/build/worker/solver/UI或读owner/key，不是视觉/平台运行通过。
