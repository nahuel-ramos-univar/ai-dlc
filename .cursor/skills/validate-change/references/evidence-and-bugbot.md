# Evidence and Bugbot

Evidence identifies the checked revision, uncommitted state, command or inspection performed, result, and acceptance criterion covered. A test command that did not run is unavailable, not passed.

`validate-change` owns Bugbot coordination. For a code change in this flow, attempt the real supported Bugbot invocation without asking the user to request it again. Use a supported host facility to run the official review-bugbot skill or the host `bugbot` subagent. If that facility is not available, ask the developer to run `/review-bugbot` and mark Bugbot pending. Never invent findings. Never claim it ran without a real result.

Do not declare delivery ready while Bugbot is pending, partial, or an execution error, unless an explicit applicable policy permits an approved exception.

A launch of Bugbot in another chat does not count as this run's review. Static contract tests in this plugin do not prove that Bugbot was invoked.

Record, for the review that actually ran:

- repository;
- reviewed diff and working-tree state;
- whether the run finished;
- whether the review was complete or partial;
- findings, or a visible no-bugs result;
- later edits that invalidate that evidence.

Status vocabulary:

- **passed** — a complete review finished and reported no code findings;
- **failed** — a complete review finished with code findings;
- **partial** — some but not all of the intended diff was reviewed;
- **execution-error** — the review did not run or did not return a real result;
- **pending** — waiting for the developer or the host to run it;
- **not-applicable** — used only with a concrete reason, for example that this run changed no code.

An execution error is not a code finding. A partial review is not passed. A pending review is not passed. A result of no bugs is not evidence that acceptance criteria passed. Later edits invalidate the Bugbot evidence tied to the previous code state.

Remote Bugbot depends on actual repository and pull-request settings. Do not promise remote execution, deduplication, or billing behavior. `validate-change` records Bugbot status from the result this run obtained, from evidence the developer supplies, or from checks that are actually visible. It does not merge, and it does not infer a result that was not observed.
