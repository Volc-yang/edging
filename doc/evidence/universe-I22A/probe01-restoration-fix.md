# p1 恢复失败：窄修与未知项

p1 result 原件 SHA `6310bee6c44c2f38c6110c9dfa9da1e54d52ecb41d61e959f56a4e15a63e7c67` 只记录恢复失败，日志未保存 before/after 字段；进程已结束，**不能声称已观察到尺寸或某个具体flag差异**。p1日志确认StaticMeshEditor/AdvancedPreviewScene模块实际加载，失败仍不是完整能力通过。

安装 `Texture.cpp:772–778` 明确对当前TC_Normalmap/TC_Masks等强制SRGB=false。旧恢复先设SRGB再还原compression，会使恢复true被当前数据压缩再次清掉；本补丁将顺序改为compression→SRGB→flip。全部flags/尺寸/身份严格原值比较仍保留，不加容差、不忽略尺寸。该顺序修复有源码依据，实际是否解决p1仍待最后p2观察。

`Texture2D.cpp:1357/1423` 的Blueprint size在GetSize为0时返回profile/source LOD fallback，否则返回platform尺寸；其注释承认fallback不精确。尚无p1真实数值可将异步尺寸变化诊断为原因。安装TemporarilyDisableStreaming、BlockOnAnyAsyncChange、FAssetCompilingManager.FinishAllCompilation声明均非UFUNCTION，未盲目调用不存在的公开Python binding，也未新增C++或全局console替代。

恢复现在尝试所有clone并逐项保存before/after/diff，保留主异常及完整traceback，再独立重查原Engine对象/包；只在全部记录后汇总失败并写入Native FAIL error及UE日志。原异常不再被首个恢复异常抹去。AST与diff检查通过，未运行UE、未写DevSSD、未修改p1/a1或发布。
