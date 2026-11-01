# Fixed Universe Authority v0.1 vectors

`positive.json` is a closed, new-domain, test-only archive: genesis revision0,
then two neutral +1 transfers at the same tick0, revisions1/2. It contains 24
records and a single pinned root with 3 retained manifests. Physical input is
explicitly `adapter_kind=fake,test_profile=neutral-transfer-v0.1`, not Genesis.
`trusted_receipts.json` is a **separate injected fixture trust anchor**, never a
field accepted from an archive/request; extra conflict-case approval anchors are
intentional. Real trust/authentication needs its own owner-supplied verifier.

`golden.json` freezes per-record `canonical_hex` and domain-separated `sha256`.
`negative.json` stores literal raw JSON inputs and required error codes; wrappers
are fixture packaging, so a `raw` string may exceed the domain string-size cap
without changing that cap for the decoded input. Wrapper size is bounded to
64 MiB; individual domain input remains ≤1 MiB. All vectors were authored once;
there is no regenerate/update-expected mode in the validator.

Run read-only main validation:

```
python3 scripts/validate_universe_authority_fixtures.py
```

Independent recomputation entry point: a reviewer should read `positive.json`
and `golden.json` directly using a separately written encoder, without importing
`validate_universe_authority_fixtures.py`; canonicalize each record according to
contract §1 and compare **both** bytes and `SHA256(prefix+bytes)` to each fixed
entry. Prefix hex is
`65646765776f726c642e756e6976657273652e617574686f726974790076302e3100`.
Report exact fixture hashes, method, interpreter and observed result in independent
review evidence. Merely calling the oracle's canonical()/digest() from another
file is not independent recomputation. The coordinator owns that review archive.

No test command opens a writer root or mutates fixtures. The checker does not
implement runtime modules, claim cross-process lock correctness or validate
hardware durability. All old profiles/data are unchanged.
