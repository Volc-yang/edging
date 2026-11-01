# I8–I12 执行依赖细化

2026-11-02，root统筹裁决；用户已授权按任务树分配并实现。原I0–I12目标/最终阶段门不变。理由：E6/E7/I9/I0A已接受，wire/provider/owner bootstrap接口已冻结，真实Genesis默认值及物理失败只阻塞真实接线，不应阻塞互不重叠的CPU构造与mock检查。

| 子节点 | 输入/允许工作 | 实际接受门 |
| --- | --- | --- |
| I8 | 真实B/O测量、provider与独立物理探针；当前首build配置不匹配fail，零步诊断受控 | 原G-P1仍须真实两臂/恢复证据，不放宽 |
| I10A | E4/E5/E6/E7及冻结v0.2/GenesisProvider接口；只实现单root worker/初态、owner-config/public-pins与synthetic CPU检查 | 源码/独立review/CPU/CI；不宣称真实worker门 |
| I10B | I10A合并及I8/G-P1，通过准确实际B/O/assets/context接真实provider并验证JSONL初始化/推进/历史/恢复 | 原I10真实运行门 |
| I11A | I9/E7、冻结wire和I10 owner CLI/publicpins；实现新Host、严格transport/control parser、mock协议与投影/launcher检查 | 新源码/独立review/CPU/NoUBA+NullRHI；构造门与真实链区分 |
| I11B | I10B与I11A准确合并树，核对新模式/owned worker入口 | 原G-B1，不能由fake回包宣称真实组合 |
| I12 | G-P1、I10B、I11B/G-B1与独立R-12卡 | 原G-B2，非相关实现owner执行真实UE↔worker↔Genesis、原图/逐动作map/恢复/真实exit |

各子节点仍归原I父卡；不并行猜接口，不把A分支通过或PR合并视作B/组合接受。新证据如要求改接口，由root先裁决再同步依赖。

I10A独占 `engine/universe_authority/{worker.py,world_initialization.py}`、`tests/test_universe_worker.py`、`doc/evidence/universe-I10/`。I11A独占Host Universe GameMode/Actor/Hud六文件+ProtocolTest、JsonlClient两文件、UniverseObservation两文件、launcher及`tests/test_unreal_mac_launcher.py`，共13源码路径，另加I11证据目录。两者无写重叠。I8仅adapter/probe/I8证据目录。统筹独占本文件、register/backlog。

I10 owner-config exact7 keys为config_version/mode/context/session/key_dir/scratch/inputs；public-pins exact12 keys为domain/version/profile/world_id/authority_root/trust_algorithm/trust_anchor/artifact_class/expected_build/expected_options/principal/allowed_actions。`--owner-config ABS --print-public-pins`只安全读ownerfile并派生public值，不读key/inputs、不lease/Genesis；正常CLI仅`--owner-config ABS`。默认existing，显式owner initialize模式才允许注册，仍需显式initialize请求。private0700目录/0600file、canonical/nofollow/nlink1/ownerUID、读一次freeze；publicviewerfile由trustedlauncher独占新建。复用public records.wire；无合法ID的畸形frame关闭channel，合法业务错误按冻结envelope；unknown回包后退出等待新owned进程恢复，禁止自动重发新意图。

I10 typed技术槽明确36（存在9、场所6、路线2+段5、水系1+段2、绑定2、world1、config1、transform1、projection1、规则2、D/budget/cursor3）。scene为world描述alias；其他类别为0而非伪造记录。资产、身份B/O、物理样本/snapshot/raw另账计件/bytes。此profile initial cap36/current typed≤288；S_records30/H≤64独立，旧U8 initial≤32不称通过，不套每步+4或宣称G-Q。

I11明确1/2仅选择weak/strong并显示，Space闩锁发所选case physical（默认weak），R显式retain；history/unconfirmed/unknown/busy拒写，history pair从已验证prior manifest/state导出。默认legacy和既有Causal/Chaos实现保持；只读Actor/相机/HUD不调用演化。真实资产图按同world/id=asset-manifest-runtime与I0A export精确匹配；仅editor-source门，不称cook/许可/写实。作者不额外运行Metal展示，统一留给I12独立门。

A分支CPU可使用显式synthetic上下文/in-process fake factory，CLI/JSON不提供fake开关；不把fake raw重标为真实Genesis/G-P1证据。资源卡逐节点另发：I10A B-C≤120s/raw64MiB，I11A CPU≤120s/raw16MiB；I11A的UE构建窗口等GPU资源释放再准入。原失败、源SHA与证据全部保留。
