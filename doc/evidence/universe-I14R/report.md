# I14-R 集成与验收状态

root owner；非owner审查待收。基线d5b54262a4c1c18d0b9e88cd712089082bcb5d50，包含独立PR111(V)/112(D)/113(L)。本任务独占shared runner/verifier、CLI定向测试和本报告；没有新运行卡、UE/Genesis/UI/provision/key操作。

## 已接线

- `i14-plan`调用真实D manifest_v2/readiness_v2、L v2资源表和V现有语义缺口。只输出提案与缺口，绝不授权运行。
- `r13-controller`要求独立card/product/tool/manifest/runner摘要及execute，固定LegacyBackend→validate_card→一个长驻DispatchController与observer。stdin JSONL只接受固定metadata协议，正常UI仍由唯一CUA owner执行；不允许JSON代码/命令/函数名。多个CLI不能重建父wait owner。未提供有效真实review/card时，在observer/child开始前拒绝。
- 固定metadata协议 `{command,args}`：begin、stage、ready、permit（即时consume一次性许可）、quit、quit_ack（仅原始请求，不当退出）、collect、seal、close。public ready/policy/action/CUA输入只能由显式ref指向controller_output/controller-inputs下的公共原件，不能重定向私密配置。每次新输入/查询/Shot均须D manifest及实际CUA原件，不能用这条metadata通道注入UE输入。
- `--i14-bundle --bundle-sha256 --i14-policy --policy-sha256`在共享verifier接真实V模块，固定注入既有inspect_authority/inspect_trace，不读取JSON函数名或passed回调，不捏造旧captured_at单点；旧bundle/authority/trace路径保留。
- EOF/异常不会把活controller JSON当wait；持续旧supervisor持有Popen直到实际wait/有界精确cleanup。abort停止observer明确normal=false，缺账本不能接受。正常seal后的stdout不写回已封存树；资源卡仍须明确所有外部输出计费范围，未来新增artifact不能复用旧snapshot。

## 实际检查

D：root10项v2定向通过；独立native源码审查无阻断；Native测试只是编译未运行。L：root28项定向/旧v1回归通过，最后7项受影响窄修复核通过；包括真实小CPU child wait/observer及合成完整账本固定点，不是UE运行。V：root最终21项通过，fake A/B组合夹具限制明确，不算真实D/L端到端证据。各独立PR最终CI均success。

root R首次6项CLI检查中3通过，3是测试夹具仅导入时临时设置scripts路径、lazy调用时路径已恢复的错误；仅修夹具让路径持续至test cleanup，3项受影响复测通过。生产CLI正常按脚本路径运行；独立review会复核最终6项，PR CI做组合全suite。未据重复运行累计虚构门数量。

## 官方CPU编译证据（无UE进程）

Native源31e38eb2b4367b272beda92a4b40a98212027468；最终D 1200287与该源的全部unreal路径逐Git差异为空，故原编译结论范围为实际相同Native输入，工具/完整Git源区分记录。

- build1：root漏带--universe，实际exit6，19.565402625s；日志PCH缺失，原件保留，不指控C++语义错误。
- build2：独立新tree/输出，同源 `--build-only --universe`，实际parent wait0，33.408370167s。累计约52.974s，共用原180s active-build预算；仅编译成功，3Native tests未实跑。
- 两日志仍出现UBA local executor；--universe实际添加-NoUBA不等于证实禁用或首轮唯一根因。第二次成功不能抹去第一失败。
- DevSSD原件根 `I14D-20261102-native-build{1,2}`，输出保持Host/plugin物理RPATH布局。无信任锚/owner配置/世界创建或迁移。

## Check / Act：仍未给实机ready

已补producer源码、实际可接的持久backend/自动wait+seal、组合verifier与CLI；真实producer来源、single-chord、原PNG、正常双会话和耗时能力仍没有新实机证据。D manifest含所有额外查询/Shot：S1 61次实际CUA调用、274s拟上限，S2 14次/100s；这些不是测量。V还明确保留既有typed-body、Static geometry/options/transform及selected Transition公开proof校验差距，结果inconclusive；不据结构相符授门。

本轮不派S，A结算no-go停止路径；工具层可接受，I14/G-B2整体未完成。I12资源2566/1200 fail及I13 partial保持原账，新增1200/2GiB提案尚未发运行卡。后续只重开实际能力采证与具体proof缺口，不重新开发已接受D/L代码；若需单独capability运行，先在新计划显式列范围/预算/原件/退出，不藏probe或补造review pass。维护UE发布版/单权威writer/抽象因果目标不变。

独立代码审查发现并修正两处CLI问题：selector后readline仍可能被无LF的partial输入阻塞，现改为非阻塞os.read、有界缓冲和截止检查；public wrapper内nested ref可重定向，现先递归限制为controller公共输入副本、已记录ref或固定公共card pin，policy也不能扩充私密allowlist。新增partial-pipe/oversize及nested-private-read负例，最终8项CPU检查通过；这些不是UE运行失败。原6项独立复跑也通过，但不用于掩盖审查发现。
