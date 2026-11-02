# I15N — exact public Native proof replay

Status: implementation complete, root review / actual build / Native run pending. Parent: I15 N; base `ee138aea8178f7d09082caf7448f6e1090719b11`. Worktree `.worktrees/i15-native-replay`; branch `codex/i15-native-replay`; PR targets `codex/plan-consolidation`. Native source frozen at `eb4c0c4a823ffb27f1bf660822fe42b8772c1f98`; Python/report commit is the subsequent task commit.

## Plan / Do

Keep the accepted Control/Observation parser unchanged. The single explicitly selected `edgeWorld.UniverseHost.PublicProofReplay` test requires opt-in, explicit public manifest/hash and exclusive output. It opens no worker/transport/world/solver. Each case loads the original public pins, reconstructs and compares exact original status/Observe request bytes, verifies original status through PublicPins and ControlParser, and uses that trusted head in the existing ObservationParser. Missing opt-in/zero cases cannot pass.

Python `native_replay.py` reconstructs serial raw stdout chunks including LF, verifies external source catalog and all original byte refs, writes exclusive case copies/manifest, and reviews actual pinned source/binaries/build/log/result/wait/resource originals. The new verification opt-in API can remove the three legacy parity gaps only for exact matched response SHA/request/context/status/selected-record outputs. Legacy APIs/constants remain unchanged. No runtime authorization or G-B2 grant is produced.

## Check actually run

- 2026-11-02: `python3 -m unittest discover -s tests -p 'test_universe_iteration_native_replay.py' -v`: **13 pass**. Synthetic framing/review positives and negatives cover original LF vs reformat, empty/duplicate/relabelled cases, source/run/watermark/ID mismatch, path redirection/allowlist, incomplete teardown, derived labeling, binary/build/selector/resource/wait/case output, and exact coverage vs unreplayed responses. Synthetic fixtures test the verifier; they are not actual Native execution/parity evidence. First run found a test expecting FileExistsError whereas the API intentionally wraps it as Invalid; expectation corrected, final suite passed.
- `python3 -m unittest discover -s tests -p 'test_universe_iteration_verification.py'`: **21 pass**, legacy behavior retained.
- Actual public I12 r4 raw chunks read and reassembled, and three selections passed `prepare_replay_cases` in an exclusive temporary directory. `old3-catalog.json` freezes original paths/SHA/identity/indices; raw sources unchanged. Initial actual raw directory contains eight complete frames (including later retain); selection is only frame3 `(0,0)`. Independent repair copy selects frame1 `(0,1)` and frame5 `(1,2)`. Each selection uses the nearest preceding successful original status. This is old proof replay preparation, not a new history/retry/solver execution.
- No UE, compiler, GPU, worker, solver, private owner/key bytes, provision/reset, or UI action run by this task. Native build/execution remain root-only pending checks.

## Root handoff

`prepare_old3.py --run-id RUN --product-source-sha PRODUCT40 --tool-source-sha TOOL40 --output-dir NEW_ABSOLUTE_DIR` prints `{manifest_ref, public_paths, case_ids}`. The output directory must not exist. Use only reviewed catalog and exact approved product/tool SHAs. Add generated public paths plus manifest to the root public allowlist. New Metal cases, if actually obtained, must be explicit source entries and selections in the same API before the one Native run; missing new responses stay missing.

APIs:

```python
validate_native_manifest(manifest_ref, *, expected_run_id,
    expected_product_source_sha, expected_tool_source_sha,
    allowed_sources, public_paths)
prepare_replay_cases(*, run_id, product_source_sha, tool_source_sha,
    selections, allowed_sources, public_paths, output_dir)
verify_native_replay_review(review_ref, *, expected_policy)
verify_evidence_with_native_replay(bundle_ref, *, expected_policy,
    authority_parser, trace_parser, native_review_ref, native_expected_policy)
```

`allowed_sources` items have exactly `{pins_ref,trace_refs,observe_frame_indices,trace_identity:{host_pid,worker_pid,generation}}`; selections exactly `{case_id,pins_ref,trace_refs,trace_frame_index}`. Public refs are `{path,sha256}`. Manifest and result formats/fields follow the approved I15 plan and module constants; real positives 1–6, derived negatives 0–2. Derived negatives cannot count as real response coverage.

Native execution receipt `universe-i15-native-execution.v1` requires `host_pid,process_start,parent_pid,argv,cwd,environment,selectors,manifest_ref,result_ref,parent_wait,normal,forced_cleanup,started_monotonic,ended_monotonic` (additional controller fields allowed). `environment` is precisely the four replay env fields; selectors exactly PublicProofReplay + IdentityAndDefaultOff + HandledInputAndOrder + PauseReadWithoutTick. Parent wait must be an actual observed 0 for the same PID/start/parent; no forced cleanup. Phase elapsed ≤180 seconds. Automation raw log must show Found4 and exactly those four Success records; result case count and input hashes are independently checked.

Independent review policy exact keys: `format,run_id,product_source_sha,tool_source_sha,allowed_sources,public_paths,approved_review_ref,manifest_ref,result_ref,execution_ref,automation_log_ref,source_refs,binary_refs,resource_ref,expected_host_pid,expected_process_start,expected_parent_pid,expected_ue_version,expected_argv,expected_env,expected_cwd,native_source_sha,build_ref`. Format is `universe-i15-native-replay-policy.v1`. `source_refs` exactly `{parser_cpp,parser_h,bridge_cpp}`; `binary_refs` exactly `{host,plugin,executable}`. Root must freeze this policy independently from reviewed actual process/build originals, not trust a proposed review's own passed declaration.

`build_ref` is a public receipt requiring `source_sha == native_source_sha`, identical source_refs/binary_refs, `actual_parent_wait_exit:0`, `build_only:true`, `ue_runtime_started:false` (extra raw-log references allowed). Actual source/binary bytes are rehashed through no-follow reads. `resource_ref` requires run_id, elapsed_seconds≤900, storage_bytes≤2GiB, all_processes_quiet:true. Root authenticates full controller observer/coverage and scope; this helper does not substitute those independent checks. Review format `universe-i15-native-replay-review.v1` requires `decision,owner,reviewer,manifest_ref,result_ref,execution_ref,automation_log_ref,source_refs,binary_refs,resource_ref,build_ref,coverage` plus format. Coverage is exactly ordered real response SHAs. Approved review hash must match the independently supplied policy.

## Act / limits

Missing actual originals return inconclusive; malformed originals or contradicting pinned identity fail. Passing review means only exact strict Native parser coverage requires final root review. Metal UI/PNG/chord/normal standard pair remain unproven; old I12 resource failure remains. Keep worktree until its own PR review/integration/test handoff and dependency audit finish. No cleanup performed.
