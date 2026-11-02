# I15 C Mac module-name correction

Root's actual I15 build exposed an admission-path defect: Mac UE5.8.3 emits `libUnrealEditor-EdgeWorldHost.dylib` and `libUnrealEditor-EdgeWorldRuntime.dylib`; C initially expected filenames without `lib`. Read-only listing of the preserved successful I14D native-build2 confirmed both actual names. The correction uses those fixed real module names in admission while preserving the existing physical project mirror, hash pins and RPATH checks. It creates no aliases and changes no binary/build/runtime behavior.

Base `5c3229c6350e20b65563354fd249642cd9f8b9d7`; branch `codex/i15-capability-mac-libs`. P independently corrects its corresponding freeze lookup in PR119.

Actual Check: `python3 -m unittest discover -s doc/evidence/universe-I15C -p 'test_*.py' -v`: 13 CPU tests passed, including a physical temporary project/module layout with the real `lib` names and no alias files. No UE, build, worker, Genesis or DevSSD mutation was performed by this correction. Root still owns the integrated real-build/admission check.
