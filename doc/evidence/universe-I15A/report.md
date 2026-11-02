# I15A — independent settlement of the bounded capability campaign

2026-11-02; reviewer `/root/i15_native`, separate from root dispatch/build owner. **Disposition: partial.** Tools and official CPU build are delivered; neither Metal nor Native was dispatched. No exact-response semantic gap or G-B2 gate is closed. This report records equivalent independent review for root integration; it does not edit the already merged N implementation.

## Fixed inputs and observed results

Product / actual successful native build: `5a6cca0c36b7dc89997d1a0bf35f154346f86e99`. At pre-dispatch review the clean tool identity was the same; after the observer correction the tool integration advanced, without a new product build or second dispatch. Storage is `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe`.

| Check | Independent observation | Disposition |
| --- | --- | --- |
| Official CPU build | First source `e51dcf8`, actual wait6 / 32.628994s, retained; sole link failure `_GDynamicRHI` from GameMode diagnostic. Native bridge compiled. Private RHI module dependency fixed; build2 at exact source5a6cca0 actual wait0 / 6.841073s, raw console Succeeded. Cumulative39.470067s<180. | pass for the final CPU build; first failure preserved |
| Actual sources/binaries | Rehashed parser cpp/h, bridge cpp, installed UE executable and real `libUnrealEditor-EdgeWorldHost.dylib` / `libUnrealEditor-EdgeWorldRuntime.dylib`; all matched build receipt and were regular nonsymlink files. Product identity passed its exact six approved output/config exceptions; tool identity clean. No compatibility alias substituted. | pass for pinned build identity |
| Old proof preparation | Actual raw trace chunks reconstructed; manifest1c17bf1a validated using explicit catalog/public allowlist. Three cases `(0,0)`, `(0,1)`, `(1,2)` bind original request IDs, LF bytes, nearest preceding successful original status and public pins. | pass for preparation only; actual Native parsing inconclusive |
| First controller | Actual outer parent wait2. Transcript rejects start_native with `continuous observer required`, then wait/seal; final abort normalfalse. Events only dispatch, metal_not_dispatched, native_manifest_frozen. No spawn event, Native log/console/result, or Native phase in abort. `capability/native/user` is an empty pre-spawn directory. First saved process sample had no UE/worker. | fail: observer callback accessed missing PID in skipped phase; no Native launch |
| Narrow correction | Reviewed skip/noPID callback guard, first actual-sample barrier and explicit stop/join/failure receipt; independent C CPU suite16 pass, including actual observer→skip→real manifest freeze with no startup sleep and timeout-thread cleanup. Final PR121 CI/integration reported by root; these CPU checks are not a runtime replay. | code correction accepted; runtime pending |
| Campaign budget | Campaign arithmetic exactly first outer monotonic1182671.312779333 → seal1183442.740305041 =771.427525708s<900. First aborted controller subtotal0.066s is not substituted for the whole interval. Actual full root stat sum at independent review1,471,486,313B; sealed conservative1,471,501,078B includes remaining14,765B allowance and is <2GiB. | pass for measured/sealed time and bytes only |
| Continuous observer | First callback failed; correction interval has no continuous process observation. Campaign explicitly records continuous_observer_pass=false. Final process snapshot has no relevant UE or worker; this does not establish uninterrupted observation during the gap. | fail/inconclusive for full-cycle observation; no continuous-observer grant |
| Authority read-only | Before/after public maps agree on all61 files; independent fresh authority map matched all61. Final public raw process snapshot classifies no UE and no inherited worker. No owner/key contents were read by this reviewer. | pass for boundary maps and final quiescence; not a Metal action matrix |
| Metal / Native | Metal explicitly skipped because CUA unavailable. After correction, remaining187s was below the required270s complete-dispatch reserve, so root did not make attempt2, prepared/card/manifest2, or another UE window. No actual Native argv/PID/wait/result exists to review. | both skipped; exact Native coverage remains empty |

## Evidence bindings

All refs below are immutable public originals under the storage root, not recreated runtime observations:

- `prep/build-receipt.json`: `85988e89bce7f6f4d0327a27dde58947f970664c3b5c9c2dc19a8ed399cbc6d2`; references failed and successful raw build/console originals and exact source/binary refs. Original failure remains exit6.
- `prep/prepared.json`: `152f968c657aef262731c5e33cc1f62f4b92acb309471a9a719de02ffb952af0`; original corrected preparation refs remain preserved.
- `prep/capability-card.json`: `dc9ef99dd38881eb194fef9f739750fa7439b4ba8ff043d44797c5ab5c7e30d0`; `replay-old3/manifest.json`: `1c17bf1abf14cbb9215aaeb830f423b885506f895190c2e3519e36f5ffbe3ee5`.
- `capability/abort.json`: `425c310273277def0cf4de12b7b0a5bd68919bab1ef1e1c4b2383fb5ef44748a`; `prep/controller-outer.json`: `67a55f957ef840bde8cb1ec1c4e9142d52802cf11e7a16dd2d1eddb73212bc51`.
- `prep/campaign-resource.json`: `cd01220ccf0a597a5a730b7baa0e5c9cf666510d4e634269abab8dad3728f718`; independently rehashed its four nested refs. `prep/final-processes.ps` SHA `0ddcc1f7ab463b00930b1c6129aebce260929f52d01a82d131daa9a9724e70a1`; `prep/authority-after.json` SHA `d896d4a81374ac713a40deae288234bd430c4c27c27ee6a3219f8d45839b3e7f`.

This reviewer read only public code/build/trace/result-index/process/map artifacts and filesystem metadata. No UE/worker/solver/UI launch, private owner/key read, provisioning, authority write or new runtime-state creation occurred. The report lives in the repository, not the sealed storage root; it does not consume the remaining sealed-output allowance.

## Act / next-cycle entry

Accept the delivered implementation and finite CPU/build checks. Keep strict Native replay, actual input/PNG, normal standard sessions and G-B2 open. Preserve I12's2566/1200s failure and I15's build/observer failures; no Native review/policy with a pass decision is created because the required actual result/wait originals are absent.

**The next single ready runtime node is an independent Native-only old3 replay**, after offline preparation from the corrected merged tool source. Review the unchanged built product/native source5a6cca0 and actual binary hashes; freeze a fresh tool identity, explicit existing-only fallback decision, exclusive new prepared/card/manifest/output refs and full resource budget before dispatch. Establish the first actual observer sample, then dispatch once and verify four exact automation tests, all three cases, original sources/binaries, actual Popen argv/env/PID/start/parentwait, continuous observer, complete bytes/time and final quiescence. The old failed card/output is not reused. Preserve all inherited inputs and restore no world state. A successful new Native run would cover only exact old responses; Metal remains a separate future node requiring CUA availability and its own approved bounded scope.

The N worktree contains only this new report commit after its previously merged work; it may be removed non-force once root integrates this report and verifies no retained configuration depends on the N path. Build/tool trees referenced by retained source receipts need their own dependency disposition before cleanup.
