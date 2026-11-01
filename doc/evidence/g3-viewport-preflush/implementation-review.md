# H1e implementation review

This is the implementer's review; independent acceptance belongs to coordination.
The candidate is diagnostic and opt-in, not an accepted product repair.

- Installed release-source order was checked read-only: Slate's public window
  destruction event precedes `NotifyWindowBeingDestroyed`; the game's close
  callback releases its viewport owner in the latter. Engine-source hashes are
  captured to prove the installation was not edited.
- The custom client uses a public `UGameViewportClient` override and an
  `AddUObject` delegate. It does not replace the native close handler. The
  callback filters to `GetWindow()` pointer identity, checks GameThread, logs
  its non-owning scene-viewport pointer and only then performs the opt-in flush.
  Other windows do not incur a flush.
- The delegate is removed on client destruction when Slate still exists; a
  destroyed UObject cannot be invoked by its weak UObject binding. There is no
  viewport shared-reference retention, custom deleter, ownership cycle, delayed
  delete, assertion suppression or permanent reference leak.
- The experiment expects a non-null owner at notification time. A null owner,
  changed owner across flush, absent callback or unavailable Slate invalidates
  that sample's mechanism evidence even if exit happens to be clean. Logs must
  establish those conditions; a clean process exit is not sufficient.
- Both arms use the same adapter/configuration and binary, with only
  `-EWDiagPreflushViewport` differing. The option defaults off. No GameMode,
  authority, camera, HUD, input, light or rendering-thread default is changed.
- The automation test uses a surrogate shared-reference probe, not a real
  native window or FSceneViewport. It verifies that disabled synchronization
  leaves queued work pending, enabled synchronization drains it while the
  GameThread owner is held, and final destruction occurs on GameThread. Its
  event timeout still releases the render waiter and drains before stack state
  or pooled events are destroyed. It does not replace real window A/B evidence.
- Remaining review limits include repeated Init/PIE, multiple windows/clients,
  platform variation, arbitrary callback interactions and stress reliability.
  One client's normal standalone Init/BeginDestroy lifecycle is the tested
  scope; no broader lifecycle or universal deadlock-freedom claim is made.

Reporter cleanup is part of evidence handling, not a viewport fix. Match only
this run's UE PID in the crash directory and its exact worker state directory;
archive before TERM, preserve unmatched reporters, and retain failed cleanup
attempts as well as corrected attempts. Do not use global process termination.
