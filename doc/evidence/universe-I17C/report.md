# I17 C：Mac Native 参数与写者完成封存

2026-11-07；输入f8d4822；owner `/root/i17_controller`。仅Python工具/CPU回归，未运行UE、build、worker、Genesis或UI，未写DevSSD、未读取owner/key。Native源、严格parser和旧review验收不变；真实四测试/case3/正常退出/资源门仍待root实跑。

Mac的LaunchMac.cpp116–117会把`$`转换成引号。新argv用四完整名称的`^`前缀，保留实际Found4、四完整Path/Success的集合门。启动前逐字节验证prepared native source pins并保存项目test inventory；当前63个源码文件、23个注册，四前缀各唯一。按UE默认IgnoreCase比较冲突；相关complex/dynamic umbrella、非literal和额外大小写变体均拒绝。inventory是已固定项目源的证明，不能替代实际automation结果。

Native DDC使用唯一真实短目录 `output_root/ddc-i17-<sha16(run_id NUL controller_output)>`，独占创建且纳入原root计量。FileSystemCacheStore.cpp70–78/3068限定Mac缓存根长度<119；原长native/ddc会达到125。新路径拒绝symlink/逗号/空格/`$`/括号及过长值；固定FileSystem完整图、Clean/DeleteUnused=false和`-DDC-NoDefaultGraph`，不继承Editor路径覆盖。最终日志须出现实际Isolated writable路径，出现Zen launch则失败；不能静态保证全部外部模块不写其它目录。

父进程实际wait后，在原180s phase/900s global剩额内等待观察器的三个连续新样本确认全部owned后代/extraUE静默，并证明console、ue.log、replay-result三文件的SHA/size/inode/timestamps稳定至少0.75s。未完成只记录normalfalse、延期路径和null原件引用，不把仍可能写入的文件称为final。完成后引用已核字节；seal在observer最后样本前后再验所有frozen文件。后代超时不kill当normal；旧失败原件不覆盖，原console不做伪恢复。

实际CPU检查：新9项通过（新增入口 `tests/test_universe_native_completion.py` 可被CI的unittest discover发现），旧18项通过。新检查包括Mac截断复现、实际项目inventory、ambiguity/complex/nonliteral/case variant拒绝、短DDC绑定和路径约束、真实短Python持stdout后代、预算到期失败/延期原件，以及封存后追加拒绝。另casefold修订后实际跑受影响inventory2项通过。真实ps/短child测试经明确本地scope自动审批升级运行，未联网/UE。`git diff --check`通过。合成日志/manifest只作CPU夹具，不冒充UE结果。

root和独立reviewer需审具体diff、最终CI与Native实际原件；卡/36字段/API未新增必填项。新增inventory、writer barrier、ddc_path/ddc_arguments、evidence_frozen/deferred_evidence_paths为执行收据附加数据。失败时null refs本来就不能通过成功Native review。全外部写域baseline/after与完整归属仍由root独立复核，不能仅靠DDC参数宣称字节门通过。
