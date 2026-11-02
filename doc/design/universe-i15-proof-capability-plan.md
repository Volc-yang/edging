# I15 PDCA：精确公开proof回放与一次只读能力采证

2026-11-02；parent G-B2；root统筹。输入 `8f7b762474a73021e097060e2a7081e5c2e06989`、[I14结算](../universe_i14_execution_register.md)。用户授权执行下一轮。方案已由三只读agent审查、root裁决接受，先调查后实现；既有D/L不重写，旧I12资源2566/1200 fail与I13/I14 partial不覆盖。

## 父节点 P/D/C/A 与依赖

P：关闭具体缺口而非再造通用框架：复用已接受UE严格parser的Record/Static/Transition路径，实际执行精确原始响应回放；用独立只读能力卡实测producer/chord/PNG/读回/退出/耗时。能力验证不以已有相同能力pass为前提，避免循环门；标准双会话/R13 ready规则不放宽。UE发布版/单writer/抽象Seed→Tree原则不变。

DAG：`0接口 → [N Native回放+审查适配 | P只读probe作用域/分镜/准备 | C能力专用控制] → R审查/集成/CPU build → M一次Metal只读 → X原始trace重组/manifest冻结 → T一次Native回放 → A独立结算/上下文commit`。M失败不自动重试，T可回放已取得且完整的响应及旧三个case，不能补造缺失新case；若M没有可用新响应，只报告旧case范围。R no-go/任意中止均直达A，未运行项skipped。

实机scope明确不是标准S1/S2，不初始化、不prepare/advance/physics/retry、不授G-B2。只派一次Metal与一次Native，**先Metal后Native**，以便一次回放覆盖本次新响应，避免隐藏第三窗口。叶任务独立worktree/branch/PR，目标codex/plan-consolidation；root审差异/实际checks/CI后集成。基线由本方案审定提交固定，同一输入不猜测接口。所有subagent仅CPU定向测试，不build/UE/solver/UI/provision/key读取；root唯一占有构建/运行窗口。

## 0：只读调查裁决

- I12 r4真实原始trace可给初态(0,0)、retain(0,1)、physics(1,2)三positive响应。PublicPins→原status严格Verify得到TrustedHead→原Observe Verify，真实Record/Static/Transition均在现有入口执行；不能从observe.head自造信任，不把旧trace叫作history/retry。
- 现producer existing只arm s2，但所需动作在s1；必须新增独立probe作用域，不冒充initialize。
- 原owner允许写；未知chord顺序可能先H后Space。必须派生**existing/can_initialize=false/allowed_actions=[]**元数据与对应pins；现typed接口允许空动作，UE BuildPrepare发送前拒写，worker也拒写。保留原owner/world/anchor/key目录引用，不读/复制/hash key内容，不provision或迁移authority。
- 旧R12要求init-first、双action且authority在新storage内，不适用此独立探针；新卡须独立严格校验，不能伪造R13 ready或放宽v1。

## N：精确Native回放与语义review适配（owner投影agent，root审查，depends=0）

D排他路径：新增Host `EdgeWorldUniverseProofReplayTest.cpp`；`scripts/universe_iteration/native_replay.py`（公共原始trace case准备/报告验证）；`verification.py`中独立新版本review分支与对应定向tests；`doc/evidence/universe-I15N/`。不改Observation parser或世界模型；P的Diagnostics源不重叠。

Native精确selector `edgeWorld.UniverseHost.PublicProofReplay`。默认不运行/不读取环境外文件；明确optin后缺manifest或SHA错须失败；不能以skip/零case当通过。只读root显式公共manifest+SHA、exclusive output；每case独立pins/status request+原response/observe request+原response及trace块索引、期望requestIDs/triple/context。原stdout chunks按serial重组，保留LF原字节，不json.dumps伪造原响应。先PublicPins(FixtureOnly=false)，用原status经ControlParser得到TrustedHead，再ObservationParser::Verify(FixtureOnly=false)；不调用LiveReadOnly/transport/worker/assetCollect/solver，不新建世界。

Native输出每case接受/错误、实际输入SHA、selected Manifest/State/Event/records摘要、parser/bridge身份和exclusive结果。derived负例明确标源case及派生，不当真实trace。原三positive覆盖初态/retain/physics；本次完整Metal新observe在M结束后加入同一manifest（预计startup current、history、held返回current，实际缺失不得补造）。

review API建议固定 `verify_native_replay_review(review_ref, *, expected_policy) -> dict`；policy精确来源由owner给机器schema并root复核，至少绑product/tool、parser cpp/h/bridge真实SHA、Host/plugin/UE版本及binary SHA、每pins/status/observe原件及trace帧、selector/argv/env、实际PID/start/parentwait0、实际found/Success+case输出、完整资源费用。callback passed或owner/reviewer名字不同不证明真实性。V只在外部独立审定review与实际archive/trace内容逐字一致时，**仅对对应exact response SHA**解除三项差距；其他响应仍inconclusive，原常量/旧API不静默改pass。不授Metal/PNG/输入/双会话/新solver或私钥真实性。

C：CPU负例覆盖缺/重复case、错原件/请求水位/source/binary/selector/normalwait、派生冒充原件、路径重定向；Native代码经root官方build，实际T才记录executed。A：缺真实Native输出/退出不解除gap，局部失败只重开N。

## P：只读probe producer/动作/准备（owner验收agent，root/u7审查，depends=0）

D排他路径：既有 `EdgeWorldUniverseDiagnostics.{h,cpp}`、GameMode.{h,cpp}仅probe读取适配、DiagnosticsTest.cpp；新增 `scripts/universe_iteration/probe_actions.py`、`doc/evidence/universe-I15P/prepare_probe.py`及定向tests/报告。标准actions.v1/v2、worker/authority/transport写协议保持。

新增显式 `EDGEWORLD_UNIVERSE_DIAGNOSTIC_SCOPE=readonly-probe`。仅真实session=existing、initialize=0、Pins.AllowedActions为空时允许p1.*；标准flag缺省仍s1/s2旧门。固定aliases p1.probe/camera/visibility/framerate/pause/history_write_rejected/held_input/final映射相应真实getter/handler阶段，原marker保留准确session=existing、不伪造init。独立probe readback format与manifest由owner交schema。p1.probe增加实际viewport_width/height、renderer和hdr以确定Retina像素与SDR，先实际Readback再Shot；标准probe旧state不变。p1.history_write_rejected/p1.held_input仍只能真实输入/回调发事件，query不造键。

public root：`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe`（独占）；继承world edgeworld-i12b-20261102-r4、旧authority-attempt4和attempt4四inputs，所有原字节/SHA核对。prepare默认审计，root显式execute才生成新0600只读owner/对应pins、新scratch、项目镜像输出映射/DefaultInput（准确白名单），不改旧源/owner/world/keys。源码/二进制/物理RPATH/私密权限/十字段context及所有间接输入严格核查；公共报告不输出私密owner原文。新产物全部计入I15字节范围，旧全部I12历史明确为继承只读依赖、不隐含搬入新2GiB。

固定最短分镜：自动status/observe current(1,2) → probe实际renderer/dimensions/quit guard+原PNG → camera旋转/恢复和三PNG → visibility隐藏/恢复和三PNG → FPS实际原值→30（原30则60冻结分支）→恢复 → pause/resume同步读回 → exact history(0,1) → 一次Space+H duration调用 → 三真实held events/释放/current原PNG → final恢复/释放 → 正常quit。至少原PNG8张；必要history拒写独立Space/R步骤须明确额外调用，不能漏报或冒称本分镜已含。本次包含独立history Space/R拒写（held前Arm→Space press/release→R press/release→Readback released→Disarm，额外5调用）；预计约48次实际CUA/4个业务请求、8张PNG，所有initialize/prepare/advance/retry必为零。额外fullscreen/resize若执行另显式计费留原件，不伪造已测时长。

每动作独占before/after与子阶段完整maps、前日志offset/新事件serial、actual CUA原件及controller时间区间；root唯CUA owner实际输入。原PNG不转码，request→stable保守区间与实际退出界。NoGF/fullscreen独立Space偏好由root在真实状态可用时操作，尺寸变化须重新读回；不盲猜窗口或在退出后查App。C：CPU检查aliases/空grants/错session拒绝、标准门不变、每call预算/恢复/原件绑定、未知chord只缺证而非pass、任何写operation/map变 fail。A：source或pins/权限不ready就不开M；实测任一项失败按scope提前收束、不现场重试凑成功。

## C：独立能力卡/持续owner（owner架构agent，root审查，depends=0）

D排他路径：新 `scripts/universe_iteration/capability.py`、对应CPU tests、`doc/evidence/universe-I15C/`。root接shared CLI；不动R12/R13标准门。复用已接受private_metadata、Python精确词法链、source identity/RuntimePins/安全原件方法，但独立typed admission要求只existing/false/[]、新root可与旧authority disjoint、公开pins导出严格交叉核查。Native没有owner/worker，Metal仅新只读owner；key只metadata路径引用，agent不读取其内容。

卡 `universe-i15-capability.v1`，scope=one-existing-metal-readonly-then-native-replay，approved root/explicit execute/有效期/一次性run；g_b2_granted=false、standard_pair=false、no_retry=true。准确product/tool/native sources、Host/plugin/UE/Python/launcher/pins/manifest/旧HEAD全map等独立expected pins，不让JSON选任意命令/代码。Native manifest是M结束后由精确trace重组的有界可冻结输入，固定注册API须验证来源范围/hash/总case数，再启T；不能为此再开第三窗口。新bridge/probe C++改变须root新build并pin，不能冒称I14二进制含新代码。

持续Popen owner/observer从dispatch预检查到两phase与最终封存，0.5s/≤2s gap；phase不能从JSON重建wait。Metal直接固定安装版App binary/Universe existing/preflush、只读pins/owner/独占trace，Native固定GameModeBase/NullRHI/精确Automation selectors。所有额外UE/selector/descendants计账；未知归属不kill，精确owned失败清理/actualwait。root UI许可只在真实PID/start/log/已验证观察且未closing时≤10s一次；首个诊断前可用实际status+observed原件作为base ready，不能以尚无自身timing/PNG拒绝能力探针目的本身。

固定session请求API/字段需owner交付与P/N互验：startMetal→ready/动作begin/end/capture准备收集→quit/actualwait→freezeNativeManifest→startNative→actualwait→seal。所有CUA仍外部，不自动注入UI；短批次每次源/PID/余量检查，退出后CLI-only。stdout/私密owner/keys索引边界明确，新增文件不能复用旧snapshot。

C：受控CPU child真实wait/observer、卡错scope/ownergrants/旧HEAD/sha/过期/重用/第三次拒绝、Native先启动拒绝、部分JSONL不阻塞、引用不越公共范围、any write op/map差/extra instance/gap/forcedexit不能normal。A：真实能力结果逐项pass/fail/inconclusive，未完成退出/封存不grant正常；标准ready只能后续独立review。

## R / root构建、实际执行和资源冻结提案

三叶审查/CI后新建准确product/live worktree，实际元数据/pins/Native manifests与所有原件留DevSSD。root可CPU官方build累计≤180s，失败原件保留/窄修计账，无UE；Runtime Host/plugin物理镜像RPATH不变。运行采用新预构建产物，不隐式build或使用含旧源码的binary。

能力global **900s**、新产物（含该root全部新增编译/诊断/trace/图片/封存）≤2GiB：Metal420=start60/interaction300/normal quit40/session seal20；Native180=start60/tests60/normal quit40/seal20；两phase间原始重组/冻结≤120、最终seal90、异常/保守余差90，共900。global连续dispatch→final seal，CPU build及此前离线准备另记scope/耗时，不能隐藏UE进程于offline。标准未来双会话卡不借用此scope，旧失败账独立保留。

Metal最迟t360正常quit、t400 actualwait、t420会话seal；Native按本phase最迟t120 quit/t160 wait/t180 seal，精确Automation queue完成-TestExit及parentwait，watchdog只失败清理。若M早结束立即收束；切勿活跃窗口长分析/大图输出。Native精确selectors已按安装AutomationCommandline源码核对PublicProofReplay + Diagnostics.IdentityAndDefaultOff/HandledInputAndOrder/PauseReadWithoutTick（4个tests、case数量单独检查），不得用prefix扫到LiveReadOnly/worker试验。无新Nativecase原件不能关闭该case的语义gap。锁屏需root在实际窗口前确认，必要时一次用户解锁；运行期临时caffeinate限本卡，结束释放，不改系统安全设置。

A独立审实际原件、卡/source/normalwait/完整预算、只读maps/trace及精确Native结果，更新各任务PR/进度/门/清理。接受probe通过项也不接受整个G-B2，不把旧数据当新solve/初始化/双session。没有DNS/API/engine-source修改，不发crash report，不碰主checkout或I12B保留输出。


## 0 冻结共享接口补充 v1

- P输出 `universe-i15-prepared.v1` prepared ref（private只读owner仅path/SHA，不含其内容或任何keybytes）及 `universe-i15-probe-actions.v1` manifest ref。新独占输出root/继承authority/4inputs/原ownerSHA/derivedfalse-emptygrants/source/tool/binaries/Python链/完整before map分别记录，C必须实际复核，不能相信passed标签。P给 `probe_manifest()`、`validate_probe_evidence(...)` 的最终机器schema供root审。p1.probe width/height取FViewport::GetSizeXY像素，renderer取GDynamicRHI->GetName，hdr取nativeShot同一Viewport->GetSceneHDREnabled；未知尺寸、非Metal或HDR开启不能通过SDR原PNG门，实际resize后重新读回。
- C API：validate_capability_card(...独立expected pins...,execute=False)→不可JSON还原ValidatedCapability；CapabilityController持久owner/observer，start_metal/register_metal_ready/permit+consume(action_id,step_id,≤10s)/request_quit+ack/finish_metal/freeze_native_manifest(ref,expected_sha256)/start_native+wait_native/seal。M fail/inconclusive后T可回放完整case，但必须实际wait/精确cleanup静默+余量足，不能抹M normalfalse。来源允许旧r4显式raw catalog+本卡Metal trace，不接受任意新增来源、零case、重复或第三phase。
- N manifest `universe-i15-native-replay.v1`：run_id/product_source_sha/tool_source_sha/cases；case精确case_id/origin(real-trace|derived-negative)/source_case_id(nullable)/pins_ref/status_request_ref/status_response_ref/observe_request_ref/observe_response_ref/trace_refs/trace_frame_index/expected{status_request_id,observe_request_id,tick,revision,watermark}/expected_accept。最多6个real-trace positive（旧3+本次≤3），派生负例若有另明确界限且不得算semantic覆盖。API prepare_replay_cases（公共raw refs、独立pins、allowlist、exclusive outdir）及 verify_native_replay_review；N实现确切Python签名及时通告C/root，不猜共享函数。
- Native env白名单固定 `EDGEWORLD_UNIVERSE_NATIVE_REPLAY=1`、`EDGEWORLD_UNIVERSE_REPLAY_MANIFEST`、`EDGEWORLD_UNIVERSE_REPLAY_MANIFEST_SHA256`、`EDGEWORLD_UNIVERSE_REPLAY_OUTPUT`。native结果 `universe-i15-native-replay-result.v1`：manifest实际SHA、hostPID/UEversion/bridge_format/case_count/cases（每case源、实际input SHA、request IDs/triple、accepted/error、manifest/state/event/selected-record digests）。源码身份不靠echo环境自证，外层review绑定真实code/binary/argv/PID/wait及所有原件。
- Native启动只有一次RunTests：四个精确 `^selector$` 用字面 `+` 合并成同一个argument，不能多个RunTests相互覆盖；`-TestExit=Automation Test Queue Empty`。实际found=4、四精确Success、PublicProofReplay case_count另核。参数由Python argv直接传字面 `$`，不经shell展开。默认误选但无optin/manifest不能当Success/零case通过。
- 版本边界：新能力卡/新probe行为/精确native review均独立；旧标准R12/R13/I14记录不放宽、不更名为probe成功。C与P/N可以单向import纯数据校验，不能循环；shared CLI由root在三叶审查/CI集成后独占修改。运行前准确source/native inputs/binaries/卡/manifest/hash再冻结。

## 执行修订 v2：界面控制器未连接时的独立 Native 路径

2026-11-02 root 裁决；实际工具目录没有 `mcp__cua_repl`，已连接 node REPL 检查 `typeof cua` 为 `undefined`。不能执行已批准的 Metal UI 动作，也不能改用 shell/AppleScript/CGEvent 绕过界面限制。此为环境能力缺失，不是 UE 运行失败。

允许最窄新增 `skip_metal`：仅在任何 phase 尚未 dispatch 时，读取 root 冻结的 `capability-skip.v1` 公共证据，精确绑定 run_id、`reason=ui-controller-unavailable`、`metal_dispatched=false`、`decision=inconclusive`，保留 M 未执行。之后可准备并执行 **一次 Native**，仅回放已有三个原始响应；仍用准确新构建、持续 owner/observer、180s phase/900s global 与完整 actual wait/seal。不能虚构 Metal normal、PNG、输入或新响应，不能增加窗口或重试。原标准双会话和 G-B2 的验收不变。

依赖变为 `R → M 环境能力检查 → [可用：原 M/X 路径 | 缺失：显式 skip + old3 冻结] → T → A`；其他任务所有权/接口与审查门不变。C 增加该 typed 分支和 CPU 拒绝测试；root 独立复核后才使用。缺少 C/N/P 交付或准确二进制时仍不开 T。

## 前 dispatch 纠正 v3：观察线程须支持未运行阶段

首个控制器 `capability/` 于 monotonic `1182671.669250291` 开始，skip 与 old3 freeze 已完成，但观察回调读取 skipped Metal 的不存在 PID 而中止；`start_native` 被拒绝，**没有 UE Popen/spawn 或实际 Native 窗口**。CLI 实际退出2，`capability/abort.json` 和 `prep/cli-transcript.jsonl` 保留，不算成功。

root 接受最小 C 纠正：观察回调忽略无 PID/跳过阶段，并校验首个样本就绪；CPU 回归与独立审查/CI 后，允许明确的新卡和 `capability-attempt2/` 控制器使用**仍未消耗的唯一 Native 窗口**。这不是自动重试已经运行的 UE。原卡/准备/中止原件不覆盖；新 prepared 仅更新准确 tool source，product/native/source/binaries 保持成功构建 `5a6cca0`，新旧 prepared 的差异与 provenance 另存公共原件，不重新构建或伪造同源。

900s 从首个 dispatch `1182671.669250291` 连续计至最终 seal，包含此次纠正和两个控制器的所有实际间隔；新控制器局部时钟不能重置总账。启动前必须至少余270s，Native 仍180s上限，最后独立复算全体原件字节和进程静默；超预算/新卡未就绪则直接结算，不再派窗口。标准门和 G-B2 不变。
