# I18A — independent finite Native proof acceptance

2026-11-07; reviewer `/root/i17_review`, separate from root execution owner. **Accept the I18 Native-only replay/evidence gate for exactly the three original responses listed in native-review.json.** This does not grant G-B2, Metal/input/PNG acceptance, a new Genesis solve, or a normal standard two-session result. I12/I15/I16/I17 failures remain unchanged.

## Reviewed inputs and execution

Reviewed plan cf76b7a and the fixed execution driver. Required two small corrections before freezing it: explicitly collect os.walk traversal errors, and turn post-run frozen-file read/mutation exceptions into a failed automatic resource receipt instead of losing final evidence. Independently syntax-checked the final driver without executing it. This was a versioned execution artifact, not a change to engine/product tools or a new framework.

Independently verified all ready refs, driver bytes c46748a2…, clean tool identity ecc2f3ddd666e34f4363ceaf4f9a296a1ec0beab, unchanged product/native5a6cca0c36b7dc89997d1a0bf35f154346f86e99, native/runtime/source pins and installed UE/real lib-prefixed Host/plugin binaries. The original build receipt remained a successful CPU-only official build; no rebuild or new product code was introduced. The three-case manifest passed raw chunk/catalog validation, the project inventory contained23 registrations with four unique IgnoreCase prefixes, and the short97-character DDC/controller paths were unused. Current61-file authority map matched. No private owner/key contents were read.

Run root: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe/I18-20261107-native-seal`.

| Required check | Independently checked actual originals | Verdict |
| --- | --- | --- |
| Actual process identity | Reconstructed PID10793, parent10778 and start `Sat Nov 7 20:54:39 2026` from the saved raw ps rows, not solely from execution JSON. The actual raw argv equals the independently constructed fixed argv, including all four no-dollar filters, NoTrace flags, isolated DDC and NoDefaultGraph. Filtered environment exactly binds the four replay variables, manifest and output. | pass |
| Actual waits and timing | Native parentwait0, no forced cleanup, normaltrue/errors empty. Native17.556088s; controller19.556623s; outer parentwait0/19.904205s; automatic driver21.290306s<900. These intervals are separately measured, not substituted for each other. | pass |
| Four exact tests | Original log contains Found4 and exactly the four required full Paths with Success; no extra test completion. | pass |
| Three exact old proofs | Ordered case_count3 and acceptedtrue/error empty. Independently checked each of the five input hashes, original status/request IDs/tick/revision/watermark, manifest/state/event digests and all selected-record output against original raw responses. Initial `(0,0)`31, retained `(0,1)`42 and physics `(1,2)`45 records. | pass for these responses only |
| Continuous controller observer | Independently rehashed and reparsed all37 raw process snapshots; maximum interval0.566936s<2. Actual observed UE identity is unique; all five observed owned identities are absent from the final snapshot. No sponsored Trace server for this Native PID was observed. | pass for this invocation |
| Cache and service boundary | Actual writable Isolated DDC log points to `ddc-i17-ac4637ba3f6534e2`; actual argv has `-DDC-NoDefaultGraph`, `-notraceserver`, `-traceautostart=0`; no Zen launch message or sponsored Trace residual. | pass for the declared configuration and observations |
| Writer-complete immutable originals | Three fresh quiet observations span1.117988s. Console1529B, ue.log185023B and result17926B have identical SHA/size/inode/timestamps in the barrier, execution receipt, driver after-check and this later independent check. Original refs still match; no derived prefix is substituted. | pass |
| Authority read-only boundary | Rehashed before/after records and an independent fresh public map agree on all61 files. | pass |
| Six declared external domains | Independently rehashed before/after refs, verified six roots and no traversal/stat errors, and recomputed the exact diff. Only three UBT rotation entries changed; conservative current changed-file bytes651. Zen, both global DDC candidates, other UBT candidate and Trace metadata did not change. | pass within the explicitly declared measurement scope |
| Complete declared resource account | Driver resource-review independently binds controller resource, outer wait, external diff, authority-after and final ps originals. Recomputed total1,586,713,405 root bytes+651 external bytes+65,536 seal allowance=1,586,779,592B<2GiB. Independent later root stat1,586,715,306B remains below that conservative total. Final relevant actors are absent and frozen errors are empty. | pass; not an OS-wide I/O audit |

The known engine startup risk from earlier Dataflow logs is not declared permanently fixed by this card. No engine source was changed, no reviewer UE/build/worker/solver/UI process ran, and no reviewer DevSSD/private-key write occurred.

## Formal machine review

- `native-review.json` has decisionpass, ownerroot and independent reviewer `/root/i17_review`; it binds the exact manifest/result/execution/log/source/binary/build/resource originals and only three ordered Observe-response SHAs.
- `native-policy.json` independently freezes expected PID/start/parent, the fixed argv and four environment variables constructed from reviewed inputs, launch cwd, and UE version5.8.3-58210709+++UE5+Release-5.8 derived from the pinned installed Build.version and checked against the actual result. It retains the existing native_replay.py schema/criteria without weakening four-test, normal wait or resource requirements.
- The review SHA is9d3b8e1d458c524dc311b559e76bc8af56216b97bea7552847f7e7c240aaa941. Its approved target is the stable integration path `/Users/yangacan/edgeWorld/edge-world/.worktrees/plan-consolidation/doc/evidence/universe-I18A/native-review.json`, not this temporary review tree. The policy and review contain no runtime dependency on the reviewer worktree.
- I ran the unchanged verify_native_replay_review against these same review bytes at the owned local review path, temporarily adjusting only approved_review_ref/public_paths in memory. It returned `checks_complete_requires_review`, coverage3; the result is saved as native-verification.json. Root must rerun the published stable policy after integrating these exact bytes; the stable target did not yet exist during this local self-check. This path publication step is not a new UE run.

Key original bindings: prepared4192e0c0…; cardbe612f03…; manifestd798c9c8…; execution1996c9ff…; UE log94a1db88…; resultd3b1bab7…; console7f89d912…; driver resource-review ea63325746854e868c06ceae3eb5e1a53dfbf583edf711cfa4290cf52ef80ca8. Source and binary originals were streamed and rehashed independently; the successful build receipt is retained from I15.

## Act and scope

Accept the bounded Native replay and evidence node. The explicit opt-in Native review may discharge the three parser-parity gaps only for matching original responses/context/status/request/selected records; unchanged legacy APIs/constants or unmatched responses are not silently granted success. Broader lifecycle/Metal/source-review conditions in an enclosing bundle still require their own evidence.

Preserve all old budget, Trace, console and incomplete-test failures under their original runs. The next parent-level work follows the real remaining world/Metal acceptance dependencies; do not rebuild or repeat this accepted Native scope merely because those broader gates remain open. This repository report and machine artifacts may be integrated as equivalent independent review, then the clean review worktree can be removed after stable-path dependency verification.
