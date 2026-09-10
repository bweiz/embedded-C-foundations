# Practicing harness engineering

The harness is this repository's navigation, explicit contract, tool commands,
and feedback loop. It is not a second model or an orchestration framework.

| Need | Mechanism |
| --- | --- |
| Discover relevant context | Short AGENTS.md files link to contract and architecture |
| Establish environment | `make doctor` checks required commands and compiler/gcov version |
| Verify work | `make check` performs a clean build and acceptance checks |
| Inspect evidence | `build/check.json`, `build/evidence.json`, `build/coverage.json` |
| Learn from mistakes | Convert a demonstrated failure into a narrow regression check |

For a task: state the requirement, read its contract, run the baseline, implement,
run the gate, inspect the diff, and report remaining uncertainty. The current
coverage task is the first exercise of that loop. A fresh agent should be able
to start from AGENTS.md without needing this conversation.

`make check` checks software and evidence behavior. It does not establish whether
an agent followed the workflow. A future agent eval must observe an actual agent
trajectory against a held-out task; checking that these Markdown files exist is
not an agent eval.

The default gate requires GCC and a matching gcov, Make, and Python 3. It has no
package downloads, API keys, model calls, or third-party Python dependencies.
Sanitizers remain a separate gate. On this hosted execution environment,
LeakSanitizer cannot inspect `/proc`; a narrower documented rerun is
`ASAN_OPTIONS=detect_leaks=0 make sanitize`. This does not validate leak detection.
