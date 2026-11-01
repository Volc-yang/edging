# H1e proposal: synchronize before releasing the game viewport owner

Status: proposed, not implemented or approved as a fix. Parent: default-thread
shutdown reliability, which remains fail/open. Start from the exact integrated
H1d SHA assigned by coordination, in a new independent worktree/PR. No engine
source edits. Do not silently make `-norenderthread` the normal execution mode.

## Evidence and hypothesis

H1b excluded worker/causal Actor as necessary triggers. H1c B2 also excluded
explicit camera SetViewTarget. Its symbolicated H1b GameThread stack waits in
`FSlateRHIRenderer::OnWindowDestroyed -> FlushRenderingCommands` while the
RenderThread releases a shared reference and calls the game-thread-only scene
viewport destructor. Release-source inspection places the engine's owner reset
in the window notification before that renderer flush. Test that lifetime
ordering directly instead of rewriting already-excluded camera behavior.

## One variable and ownership

Use the published `UGameViewportClient` extension and Slate's public
`OnWindowBeingDestroyed` notification to prototype a project-owned adapter.
Both arms use the same adapter registration/configuration; A records the
notification only, B additionally calls `FlushRenderingCommands` on GameThread
before the game's window-close callback can reset its scene viewport owner.
Filter to the owning game window, preserve delegate ownership/removal and
avoid replacing native close handlers. Keep a reviewed diagnostic toggle for
the comparison; do not publish a product default before review.

Own new viewport-client files, necessary host module dependencies/configuration,
focused automation and evidence. Do not modify GameMode, camera, HUD, input,
worker or world rules. Never leak the viewport, suppress the assertion, defer
unbounded destruction, or disable rendering threads in this comparison.

## Ordered check

1. Review the installed version's notification/owner-release order and public
   extension API. Log thread, window identity and sync begin/end; add a focused
   lifetime test that verifies outstanding render work is drained while the
   game-thread owner is still held. Track all failure paths.
2. Official Editor build; independent UserDir per arm, identical full scene,
   live Genesis, explicit tick 0/1/2 and historical/camera actions. GPU serial.
3. Interleave A1/B1/A2/B2, each initialized for at least 180 seconds before the
   same close-button protocol. Preserve native stacks on any failure, all
   original logs, close delivery uncertainty, real UE/worker PIDs and exits.
4. Recheck state/file hashes, restart recovery and no worker leftovers. A
   failure in B rejects this candidate. Clean B samples alone do not establish
   universal reliability; independent review decides whether further stress
   coverage or an opt-in project workaround is warranted.

If the notification cannot safely precede owner release in this installed
version, stop this adapter path and return evidence rather than changing UE.
Fallback attribution is repeated stock GameModeBase under the same project/map
and default rendering mode, then individually changing controller/HUD if still
needed. Stock-mode failures must not be assigned to the causal worker.

## Separate visible warning

H1d images preserve `LIGHTING NEEDS TO BE REBUILT (16 unbuilt objects)` over
the HUD. Do not hide it with screen-message suppression. Inspect runtime light
mobility/static-lighting assumptions in a separate presentation-only fix, with
before/after Metal images and unchanged authority hashes. This warning is not
the viewport assertion and is not addressed by the temporary render option.
