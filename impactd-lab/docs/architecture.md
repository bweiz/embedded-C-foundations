# Architecture

`fixture/image.c` implements the byte-format contract in `README.md`.
`fixture/test_image.c` supplies named behavioral checks and two explicit demo probes.
`scripts/demo.py` challenges one assertion with one temporary source mutation.
`scripts/coverage.py` records isolated GCC/gcov line coverage per named test.
`scripts/check.py` supervises the local acceptance gate and writes `build/check.json`.

The coverage collector compiles one instrumented executable in a fresh temporary
directory. Before each named test it removes all `.gcda` counters; after the test
it consumes gcov JSON. Tests execute serially. The temporary directory is unique
to the collector, so parallel independent collectors cannot share counters.

Reports bind observations to SHA-256 identities for the validator, header,
test source, and collector. A query rejects a stale identity before looking up
an observed line. This is conservative file-level freshness, not semantic
invalidation, cross-version line mapping, or proof that unchanged code is safe.

Coverage means `observed_execution`. Requirements remain human-authored.
There is no inferred dependency graph, eBPF sensor, or Rust runner yet.
