# Chaos presentation validation control (H1)

The control is opt-in for a local evidence run. Start `ChaosObservationGameMode` with the normal immutable seed7 arguments plus `-ChaosValidationControl=<absolute JSON file>` and `-ChaosValidationAck=<absolute JSONL file>`. Use a new command/ack pair and isolated `Saved/EdgeWorldChaos` state directory for each run. The control is polled by UE's core ticker, including while the game world is paused; it does not use the world's simulation Tick.

Atomically replace the command file with one JSON object containing a strictly increasing integer `seq`. Each new sequence produces one compact JSONL acknowledgement with `seq`, `action`, `applied`, and `detail`, and a matching `ChaosValidation` UE log line. A rejected command has `applied=false`. For asynchronous `observe` and `reveal`, `applied=true` means the worker request was dispatched; additionally require the later `Chaos origin observed committed tick N` log line and worker manifest evidence before claiming success.

| Action | JSON fields | Confirmed effect |
| --- | --- | --- |
| `camera` | `position:[x,y,z]`, `focus:[x,y,z]`, `fov:20..120` | Sets the spawned overview camera transform/FOV; ack reports the applied transform. |
| `max_fps` | `fps:5..240` | Calls the UE engine frame cap and reports the resulting setting; separately measure actual rendered cadence if required. |
| `pause`, `resume` | none | Calls UE game pause and reads back `world_paused=true/false`; resume remains available through the core ticker. |
| `visibility` | `visible:true/false` | Sets the world-spirit boundary proxy visibility only; no worker request. |
| `observe` | `tick:0/1` | Dispatches the existing exact historical Observe if the head contains the tick. |
| `reveal` | none | The only command that explicitly requests O1; accepted only once at head tick/revision 0. |

Example command: `{"seq":1,"action":"camera","position":[10000,-28000,41000],"focus":[57000,42000,0],"fov":60}`. Write it to a temporary sibling file, then rename it over the control file so UE never reads a partial command. Increase `seq` for every operation. The controller polls at 0.1-second intervals and ignores already processed sequences. It does not create or mutate the worker manifest except via explicit `reveal`; compare the manifest, state, event and head before and after every presentation action in the independent C3 review.

H1 local validation used UE 5.8.3 Editor/Game Mac Development builds and an `UnrealEditor -game -nullrhi` live chaos worker run. The command/ack/log trail confirmed camera FOV 60, frame cap 30, pause→resume, visibility true→false, tick0 Observe, one explicit O1 and tick1 Observe; a second `reveal` was rejected. This does not establish Metal visual output, actual frame cadence, or per-action authoritative digest stability; C3 performs those checks.
