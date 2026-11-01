# H-LIGHT-01：运行时光照警告

状态：统筹接受方案，先准备代码与采证入口；H1f 释放 GPU 后才构建和实测。
父节点 V-HOME 呈现质量，与退出断言分别评价。准确基线由发布卡指定。

## Plan

GameMode 动态生成 DirectionalLight 只设强度，安装 UE5.8 默认其 Mobility 为
Stationary；SkyLight 已为 Movable。环境运行时创建的 Static 组件恰为 16 个，
与未构建警告数量一致。该静态归因需以真实 `DumpUnbuiltLightInteractions`
确认，不以数量相符当作实证。候选最小变更为显式设置 DirectionalLight 为
Movable。保留静态几何、碰撞、曝光、材质与世界规则。

独立 worktree/分支；owner 仅写 GameMode 的灯具初始化小块、必要采证入口和
`doc/evidence/home-runtime-lighting/`。不触碰 H1f viewport 代码、全局配置、
Worker 或环境组件。不隐藏 screen messages，不关闭所有静态光照来消除提示。

## Do / Check

1. GPU 释放后，使用固定基线/场景/视角/曝光和独立 UserDir 保存修复前 Metal
   画面、实际 Mobility、未构建对象数与交互列表。保留真实启动与退出日志。
2. 最小修改后官方 Editor build；记录源码与 binary 哈希。使用相同退出模式
   和场景参数采修复后 tick 0/2，HUD、节点、地面与阴影须可见。
3. screen messages 保持启用，稳定观察时 `NumLightingUnbuiltObjects=0`，
   交互清单不再列出这 16 个对象。截图中看不见提示不足以验收。
4. 历史、相机、恢复前后逐项比较同一世界全部权威文件哈希。仅显式 Advance
   改变权威状态。记录真实退出码及精确 UE/Worker/reporter 清理；新崩溃另存。

## Act

若交互列表推翻归因，回报后调整卡；不扩改渲染设置。独立 PR 报告真实结果，
统筹复核并仅集成通过的修复。此门只接受运行时光照配置与警告消除，不证明
写实视觉、性能或退出可靠性。H1f 与本卡 GPU 串行，禁止修改其对照环境。
