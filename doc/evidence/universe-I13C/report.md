# I13-C passive native Shot capture

Status: implementation prepared; CPU checks pending. Base
`60857c04fa13db7b23a1f9f2668dc22842196fe9`. Owned capture.py, its focused test,
and this directory only. No UE, native build, solver, UI, owner/private/key or
production authority operations. Imports have no IO or process side effects.

## API and integration contract

All APIs raise `CaptureError` on incomplete, unsafe or mismatching evidence.
All referenced inputs must be public originals, never private configurations.
Public refs are exact `{path,sha256}`. No helper imports A/B, the authority,
Genesis or the shared runner/verifier. Paths must be absolute/canonical and
without symlinks at any component. Openat/O_NOFOLLOW anchors all directories;
regular files are bounded and rechecked for inode/stat stability. Output JSON
is exclusive0600 and fsynced; failures retain originals and reservations.

- `prepare_native_shot(*, target_path, expected_binding, trusted_head,
  selected_observation, observation_ref, before_map_ref, before_map_monotonic,
  log_path, log_offset, clock, expected_width, expected_height, show_ui=False)`
  checks an absent unique `.png` target and parent device/inode, before-map and
  upstream observation proof. Writes exclusive `TARGET.png.prepare.json` as
  reservation; returns `{preparation_ref:{path,sha256},command}`. A concurrent
  target arrival leaves a failed reservation rather than permitting reuse.
- `collect_native_shot(preparation_ref, command_receipt_ref, *, expected_binding,
  expected_trusted_head, expected_selected_observation, expected_observation_ref,
  expected_clock, receipt_path, max_wait_seconds=2.0, stability_seconds=0.05)`
  checks the independent expectations, actual CUA receipt and pinned log
  identity/prefix/range, reads and strictly decodes the original PNG, waits a
  bounded stability interval and rereads identical bytes/stat/inode. It writes
  a provisional capture JSON and returns its ref. A missing or incomplete PNG
  fails immediately; this function never initiates or retries a UI command.
- `verify_native_shot(capture_ref, *, expected_binding, expected_trusted_head,
  expected_selected_observation, expected_observation_ref, expected_clock,
  after_map_ref, after_map_monotonic, before_exit_monotonic, before_exit_ref)`
  rechecks all originals, requires the actual exit-boundary receipt, checks
  command→first read→stable→after map→actual before-exit in one controller
  clock, and compares complete authority map files. Returns
  `phase=checks_complete_requires_review`; it grants no runtime/Metal/UI gate.
  Root can preserve this return value using its exclusive evidence writer.

Binding is the exact eight fields frozen in I13-0. Head and selected observation
are separate exact triples. History can select(0,1,1) while trusted current is
(1,2,2); neither is silently substituted for the other. Expected clock is supplied
independently at collection and final validation. Maps use the existing
`{root,files,bytes?}` shape and are read as evidence only; authority is never
traversed or opened. Authority directory identity is checked as path metadata.

## Public wrappers supplied by R

R must construct the observation wrapper AFTER strict observation verification,
not from an arbitrary visual label. C checks consistency, not that upstream
verification actually ran. Observation ref points to JSON containing:

```json
{"binding":{},"trusted_head":{},"selected_observation":{},"clock_id":"controller-id","verified_monotonic":0,"verification_ref":{"path":"ABS-public-verification-original","sha256":"SHA64"}}
```

Command receipt ref points to JSON with `format=universe-i13-capture.v1`,
`phase=cua-command`, the exact `preparation_ref`, `command`, `binding`,
`trusted_head`, `selected_observation`, `observation_ref`, `clock_id`, finite
`start_monotonic/end_monotonic`, `cua_result_ref` pointing to the actual original
CUA result, and `log` copied from prepare plus actual `after_offset`. Prepare log
contains path/device/inode/before_offset/prefix_sha256; the entire prefix is
hashed and its identity rechecked. Matching a raw CUA ref does not certify its
provenance or that the image contains the expected viewport. R/reviewer must
bind actual A process identity, trace/log markers, world/projection generation,
readback, and the real CUA operation independently.

Before-exit ref points to JSON with the same format, `phase=actual-before-exit`,
exact binding/clock_id/before_exit_monotonic and `exit_evidence_ref` pointing to
the actual quit-boundary original. A planned deadline or guessed timestamp is
not this event. This final ref is provided after the event; provisional collection
is intentionally separated so no future exit timestamp is invented.

Clock is exact `{id,anchor_monotonic,anchor_utc}` with finite nonnegative
monotonic value and timezone-aware ISO anchor. The original mtime is used ONLY
for conservative stale-file sanity against the command/UTC anchor; it is never
treated as frame capture time. Reported capture interval is request→stable
read, not a precise rendered-frame timestamp. Caller must use its controller
clock without mixing unanchored UE or external process clocks.

## Native command and decoder limits

The returned native command is `Shot filename="ABS.png" nosuffix`, optionally
explicit `showui`. No startup ExecCmds, HighResShot, external screenshot,
transcoding, process, UI or automatic retry. Root must issue it only after
verified observation in the actual stable SDR viewport. Installed UE source
shows command return/delegate completion can occur without a saved file; both
are insufficient. HDR EXR and JPEG misnamed PNG are rejected by magic.

Decoder:32MiB PNG,16Mi pixels,64MiB scanlines; RGB/RGBA8 noninterlaced SDR only.
Checks every chunk boundary/type/CRC, first unique IHDR, contiguous IDAT,
terminal IEND without trailing bytes; rejects animation, unknown/unsupported
profiles/chunks. Supports validated ordinary sRGB/gAMA/cHRM/pHYs/sBIT/tRNS/tEXt
metadata. Bounded zlib decoding requires exact scanline size, EOF and no extra
stream. Reconstructs filters0–4 and reports decoded pixel SHA, preserving the
original PNG bytes and hash. No pixel checksum implies physical-world realism
or UE/Metal provenance. Unsupported valid PNG variants deliberately fail;
expand only through reviewed evidence if the actual installed encoder needs it.

## Validation scope

CPU-only focused synthetic cases cover all filters including nonzero predictor
reconstruction, malformed PNG boundaries/CRC/zlib/filter/format, decompression
caps, exact expected bindings/history/current distinction, observation/log/CUA
refs, stale/existing/symlinked/replaced/hardlinked files and parents, exclusive
receipts, changed full maps, missing/invalid exit boundary, finite clocks, and
side-effect-free imports. Source is committed before executing these checks.
No mock result proves native Shot availability, UI provenance or real runtime
duration; those remain I13-S1/R independent-review gates.
