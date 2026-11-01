# E3 Store raw 扩展接受（2026-11-02）

PR #89 source `2f76b756ee2eeb6daca218eea08efff366b9ab20`，merge `1f95fac571cb41f15296c47d6db59ba7a1ca65ab`。仅store.py/专属测试；首check142tests/17new/3.329秒/exit0，输入哈希不变，未用targeted。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/E3-20261102-attempt1/index.json` SHA `ebd3fb7f7fcf97fa94c2c3dfa2efd8347ee9974066c5e3a9141d3541fd8e071f`，12indexed files/3637593bytes，现场fault map排除外置keydir；root逐12/12文件size/hash通过。

非作者u7读完整source/两路径diff，接受：v01构造/三参PinnedRoot默认保留；v02匹配ctx/只读verifier拒signer；完整HEAD闭包含all retained raw/MAC/媒体/尺寸/class；unused与坏既有对象拒绝，不覆盖修复；raw文件与blobdir同步先V，HEAD唯一原子发布；postV unknown清record/raw cache；D_recovery重读全部JSON/raw再同步各文件/目录/HEAD/root。read_blob仅cache中合法ref并实际no-follow/nlink1核对，不求解。最终CI verify success（run41330611719/job124919711106），expected-head合并后source祖先/clean核对，task worktree清理，branch/raw保留。

E3本卡complete，扩展独立故障门E6与真实物理仍planned。E4/u7与E5/u2从同一准确merge独占worktree并行，正式B-C；E4额外仅codec.ApprovalSigner协议2方法补充，E5不得访问records私有helper。之后非作者E6，实际Genesis/Host/组合依次按依赖准入。
