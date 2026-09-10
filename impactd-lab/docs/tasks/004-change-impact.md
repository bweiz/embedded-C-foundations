# Task 004: map a candidate diff to baseline evidence

Goal: produce an explainable test priority list from changed baseline lines,
while explicitly retaining the full verification gate.

The baseline must contain source snapshots matching its recorded hashes.
The analyzer compares those snapshots to candidate files, never candidate line
numbers to old coverage. It does not execute the candidate or mutate sources.

Acceptance cases in `make check`:
- A replacement of the entry guard finds its eight historically observed tests.
- Inserting lines before the guard preserves its old coordinates in another hunk.
- Pure insertions report unknown new execution and request broad verification.
- Deleted code uses old coverage; deleting an input file requests broad verification.
- Changes with no observed coverage do not produce a safe-to-skip result.
- Header/test/collector changes request broad verification.
- A hash/snapshot mismatch, absent snapshot, or malformed coverage is rejected.
- Identical tracked inputs produce no claimed code changes.
- A candidate introducing a guard defect fails tests prioritized from the baseline.

This milestone prioritizes tests; it never permits skipping `make check`.
Scope is the four tracked collector inputs, not a complete repository diff.
The report names that scope and unobserved files/conditions as limitations.
