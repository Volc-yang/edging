# I8 / I10A 统筹复核

2026-11-02，parent=I。独立reviewer=root。接受有限G-P1及CPU worker构造，不接受尚未运行的I10B/UE组合门。

| 卡 | source / PR / merge | 实际结论 |
| --- | --- | --- |
| I8 | runtime `9270349fab51f8495cfc8d39042496ce451a2522`，final docs `e4f12f4657bde2de6a079992296a221dd2fedb68` / #95 / `51b95de102b7bde72b041ae0527533b46b48fb14` | finalCI run41338305926/job124942727136成功；root源码/原件/独立数值复核通过，G-P1有限pass |
| I10A+I10R | check `0522433`，final `3b07fdea35768d88e0759ca428ac728f12fd7bd3` / #96 / `dcfd3bcc3da9ebb894e2ea5e317ba1443f9dd9bd` | finalCI run41338446598/job124943139426成功；15CPU tests、root源码及全部raw索引/批准I0A输入核对通过，CPU构造接受 |

I8完整[报告](../evidence/universe-I8/report.md)保留首次scratch/input保护返工、pre-build O及首Scene mismatch失败、唯一零步诊断及post-build bootstrap修复。config请求max_contacts32不变，实际resolved5如实导出，六字段从公共零步build读取而非手抄。原B/O/context均保留为历史失效输入。最终adapter字节SHA `15f5b96bb0381781d0357eb93510622afe6ec3d5caf60adb5ed8190ff6abb192`；B=`289d4f525321297c5fefb0452629ec008d0a39a52cf889da37f357fcc13e2634`，O=`7165e3f027a5d5538e091e8bd48e2a738b7757401aa827a3ff0aacbb454044ed`。

root核对成功物理292原件（index `456195d2ba6a25bba0a60007d5545d7091d02feb9c39e46b0d67c3eb23552e72`）、64臂family的record引用/原始checkpoint SHA/长度、每步Fraction精确D、动态解析质量与fixed真实+0、末4gap/vz/contact、frame位姿、resume17完整sample/D。weak首次−7mm、strong−35mm，两32×8步及额外8步共520；额外tick16恢复续算exact。实际GPU累计97.687s/600s、原件约55MB/1GiB，实际child26787 exit0/reaped及destroy。此probe没有State/HEAD/command admission/Store，也未调用真实世界propose，不能冒称组合。

I10[报告](../evidence/universe-I10/report.md)保留首test错误（换approval/command IDs触发正确COMMAND_CONFLICT）、唯一修订及新I10R review卡。root发现并要求asset_audit实用核对、安全scratch复用、冻结error codes；已有HEAD在acquire持锁guard已拒，补counter0与before/after证据而不重复私有HEAD读取。初始化纯组合26→31records/typed36，真实B/O/assets/physics和key全为外部owner输入；生产CLI无fake开关。public pins CLI不读key/inputs、不建root、不导入provider。所有权、E4/E5、unknown退出及只读边界保持。

root逐字节核对I10三索引227/1019/1138项，索引SHA分别 `301676ddea37d7f91d8a4c5d92f2cfcf427ae00447224d5329d28f80c94bb35f` / `bb4d0ae8f83671b1cb915a99ce95313708dece6a01e1bd38ca2bed19e5a93ed0` / `6156c6f209eb5f17c112fe9972709d6366401d6d237e850e34b6695cc66aa347`；两approved-asset-inputs与原I0A文件一致，无key内容索引。W6恢复测试为同进程新Runtime，CLI内部子进程未单独保存PID/output的限制如实保留；实际CLI/propose/restart归I10B。

两source均为集成祖先，worktree干净。原分支/所有原件保留，批准非force移除I8与I10A任务树，下一张I10B从准确集成树新建工作树。I11R作者补齐被动raw recorder/门控retry与readonly采证操作后才授UE构建；I12由新独立owner实施，G-B1/G-B2仍开放。
