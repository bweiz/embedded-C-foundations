# Impactd lab: evidence before infrastructure

A first, deliberately small experiment toward answering:
**What evidence do I still need before accepting this change?**

This directory is independent of the repository's existing exercises. It
contains a complete C firmware-header validator and a reproducible demonstration
of a passing test that fails to verify an important behavior.

## Run

Requires a C11 compiler, Make, and Python 3 (standard library only).
The coverage/harness gate additionally requires GCC and a matching gcov with JSON support.

```sh
cd impactd-lab
make doctor
make check     # clean rebuild, suite, demo, isolated coverage, acceptance checks
make rust-check # Rust/Cargo required; unit tests and Python/Rust coverage parity
make test
make demo
make sanitize  # compiler must support AddressSanitizer and UBSan
```

Start agent work at [AGENTS.md](AGENTS.md). The [harness workflow](docs/harness.md)
describes how to establish a baseline and turn failures into executable checks.
GitHub Actions runs the same `make check` gate and sanitizers on lab changes.

## Observed execution queries

```sh
make coverage
./build/test_image --list
./build/test_image --test bad_magic
python3 scripts/coverage.py explain 25
```

`explain` takes a current line number in `fixture/image.c`; line 25 is the entry
guard in this version. `build/coverage.json` records separate execution counts
for each of the 40 named tests. The collector resets counters between tests.
Queries reject evidence if the validator, header, tests, or collector changed.
An empty observed set means no recorded test reached that line, not that the
line is safe to change. Comments and non-executable lines can also have no counts.

`make test` runs the real boundary suite. `make demo` builds baseline and
mutated validators in a temporary directory, then runs the suite and two entry
probes against each. The intentionally weak probe is explicit demo code; it
does not replace any assertion in the normal test suite.

Expected experiment:

| Probe | Baseline | Entry rejection removed |
| --- | --- | --- |
| Complete suite | Pass | Fail |
| Weak: function returns without crashing | Pass | Pass |
| Strong: exact rejection status | Pass | Fail |

The demo exits successfully only when that entire expected matrix is observed
and the strong probe fails through its intended assertion. Compiler failures,
unexpected exits, and timeouts fail the experiment. No firmware is executed.

`build/evidence.json` records source and executable SHA-256 hashes, compiler
version, build commands, probe output, return codes, the explicit mutation,
and the bounded finding. Generated files are ignored by Git. Temporary command
paths expire; `make demo` reconstructs the experiment from committed sources.
This report records observations, not an attestation from an independent verifier.

## Image contract

The image begins with a 20-byte header; every field is an unsigned little-endian
32-bit integer. Payload bytes immediately follow it.

| Offset | Field | Requirement |
| --- | --- | --- |
| 0 | magic | 0xCD |
| 4 | version | 1 |
| 8 | image_size | Nonzero payload byte count, excluding header |
| 12 | load_addr | Payload fits in [0x08010000, 0x08050000) |
| 16 | entry_addr | Lies in the loaded payload, excluding its end |

`length` is total readable input bytes including the header. The caller must
supply a valid buffer of that length. Extra bytes after the declared payload
are permitted. The validator reads individual bytes, accepts unaligned input,
and checks ranges using subtraction after validating lower bounds to avoid
integer overflow. Error precedence follows declaration order in `image.h`.

This is an architecture-neutral structural fixture: instruction alignment,
Thumb bits, checksums, signatures, rollback protection, and actual flashing
are outside its contract. A structurally valid image is not authenticated.

## What this establishes

We can bind observations to exact code, query which named tests executed a line,
reject stale file identities, and demonstrate that a specific test does or does
not detect one deliberate fault. We cannot yet infer affected behaviors,
automatically invalidate semantic claims, or prove correctness.
This is a baseline experiment using established mutation-testing principles,
not evidence of a novel impact-analysis algorithm.

## Native execution runner

The standard-library Rust runner independently compiles and runs the fixture,
isolates gcov counters, supervises direct-child timeouts, and records raw evidence.
Requires Rust/Cargo, GCC/gcov, gzip and sha256sum. No Cargo registry downloads.
`GCC` and `GCOV` for the native runner are executable paths, not shell commands
or strings containing flags. Rust captures raw gcov JSON; Python validates it.

```sh
make rust-check
# Reports: build/rust-coverage.json and build/parity.json
```

Parity compares all positive line counts for every one of the 40 tests, ignoring
incidental timestamps and temporary paths. It rejects stale inputs, altered
counts, and a failed recollection retaining an old success. Timeouts cover direct
children only; the trusted-fixture runner is not an arbitrary-command sandbox.

## Next implementation milestone

1. Map changed source regions to recorded observations, handling line movement explicitly.
2. Compare selections with the full suite on held-out defects.
3. Extend the Rust evidence/query layer while preserving the reference comparison.

Keep runtime observations, declared requirements, and inferences distinct.
Introduce eBPF only when a specific missing observation justifies it.
