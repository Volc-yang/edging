# H1d full live Genesis temporary rendering path

Base: `81bcd792708d1f801dd4f284dd121307b318ad9a`; independent branch/worktree
`codex/g3-live-safe-render`. H1c proved that skipping explicit SetViewTarget
does not prevent the viewport assertion. C1 only tested an empty diagnostic
scene with `-norenderthread`; it did not validate the real user path.

Add an opt-in `--no-render-thread` launcher option without changing defaults.
It forwards installed UE's `-norenderthread` and explicitly reports the
unmeasured potential CPU/GPU performance cost and lack of root-cause repair.
Own only the launch script, its focused mock tests, UE launch guide and this evidence
directory. Do not edit project C++, worker rules or engine source.

Build before opening the exact project. Use real Genesis Python, the owning
worktree worker, the full causal Actor/environment/HUD and a fresh isolated
UserDir. Record initial tick 0, explicit advances to 1 and 2, HUD/scene images,
history 0/1/2, H/R and camera movements. Snapshot persisted authority before and
after each read-only action. Capture startup/build phases, first observed
image, worker PID, all raw logs, process inventories and exits.

Close the first instance with the window button after at least 180 seconds
from initialization, restart with the same UserDir, verify exact tick-2
manifest/state/event recovery and repeat read-only interaction. Close the
second instance with the window button after the same minimum interval.
No concurrent UE or worker writers. Preserve failures and raw SHA-256 index.

Successful samples support an explicitly temporary launch path only. Default
threaded reliability remains fail/open, universal reliability and performance
remain unproven. If samples fail, retain that result and do not recommend the
option. Propose the next default-thread attribution card separately.
