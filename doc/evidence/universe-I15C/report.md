# I15 C — capability controller

Status: implementation ready for independent root review; UE/Metal/Native execution remains unverified. Base `ee138aea8178f7d09082caf7448f6e1090719b11`; branch `codex/i15-capability`. This task does not grant G-B2 or standard-session readiness.

The new module independently admits the exact I15 card and P's 36-field prepared artifact. It checks the clean product/tool identities, actual source/runtime/binary hashes (streaming for large binaries), installed UE5.8.3, physical Host/plugin RPATH mirror, pinned lexical Python chain, inherited private existing owner and derived false/empty grants, four public inputs, public pins, key-directory metadata only, complete authority map and HEAD. No private key bytes are read. The pure public-export preflight compares the canonical LF bytes exactly.

One live Python parent owns Popen and a continuous passive ps observer; JSON cannot restore a validated controller. Metal and Native can each dispatch at most once. A private reserved-directory path fixes double-mkdir without allowing arbitrary reuse. Fixed argv/environment select the installed project and four exact Native tests; no configurable command shell. The parent records actual wait and exact observed PID/start/argv. Timeouts/abort are forced failure cleanup, never normal acceptance. Authority maps, actual input-call intervals, raw tool refs, and request framing remain separate evidence. Native result matching here is structural; N's independent exact replay review performs semantic evidence reconciliation.

Root amendment `f8f07fe` permits an explicit no-UI skip before any UE dispatch. `skip_metal` requires exact `universe-i15-capability-skip.v1` evidence and records `normal=false`, `decision=inconclusive`. It does not fabricate a Metal wait, PNG or input evidence. Native can then replay only the admitted legacy catalog. Root reported no CUA controller available; this task did not inspect or manipulate the UI.

## Actual checks

`python3 -m unittest discover -s doc/evidence/universe-I15C -p 'test_*.py' -v` — 12 CPU tests passed. Tests include an actual short CPU child with parent wait0 and observer PID identity, an actual CPU child killed by the watchdog and retained as forced/abnormal, one-shot skip, forbidden Native-first/manifest-freeze order, expired/old card rejection, exact public-export LF, streaming >16MiB input, changed hash, symlink and key-content refusal and unlisted/private skip evidence refusal before any read. No UE, worker, Genesis solver, build or DevSSD provisioning ran. Full installed-runtime admission and exact four Native tests need root integration checks.

## Root usage

Import from the clean integrated tool root, then:

```python
v = validate_capability_card(card_path,
    expected_card_sha256=card_sha, expected_prepared_sha256=prepared_sha,
    expected_probe_manifest_sha256=probe_sha, expected_product_source=product_sha,
    expected_tool_source=tool_sha, expected_native_source_sha=native_source_sha,
    execute=True)
c = CapabilityController(v)
c.start_observer()
# Allow the first passive sample (typically <0.6s); no UE is yet running.
c.skip_metal(skip_ref)  # explicit root amendment only; otherwise start_metal()
c.freeze_native_manifest(manifest_ref, manifest_ref['sha256'])
c.start_native()
c.wait_native(timeout=180)
resource_ref = c.seal()
```

Prepare the old-three-case manifest **before** creating the controller/card: the fixed card `public_paths` must explicitly include all pins, raw chunks, reconstructed requests/responses and manifest, and `legacy_sources` must identify the original traces/observe indices. The skip-to-freeze handoff is bounded by120s, so no offline preparation belongs inside that interval. Returned result and execution refs bind the exact new output. On exceptions call `c.abort(reason)`; it records actual failure/cleanup and checks quiet through passive process samples only. Do not refresh an App binding after exit.

For future available CUA, `start_metal()`, `register_metal_ready()`, `begin_action(action_id, step_id, timeout<=10)`, actual external CUA, and `end_action(seq, raw_tool_ref)` bracket each real call. Raw tool files must be under `controller_output/controller-inputs`. `snapshot(label)` supplies complete map and log-prefix refs, `now()` supplies controller clock. Native Shot preparation/collection uses the existing `capture` API with these actual wrappers; this module does not create PNGs or inject UI. End via `request_quit(reason)`, actual UI quit, `ack_quit(raw_ref)`, `finish_metal(timeout<=40)`, then freeze/replay. The old standard acceptance branch is unchanged.

Root must review this branch and CI, integrate N/P before executing C (imports are intentionally deferred), freeze actual build receipts, and preserve failed/inconclusive evidence. Worktree retained pending independent review, PR integration and runtime transfer.
