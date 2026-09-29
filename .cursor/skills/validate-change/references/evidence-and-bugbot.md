# Evidence and Bugbot

Evidence identifies the checked revision, uncommitted state, command or inspection performed, result, and acceptance criterion covered. A test command that did not run is unavailable, not passed.

`validate-change` owns Bugbot coordination. This plugin cannot invoke Bugbot programmatically. When Bugbot is required or requested, ask the developer to run:

`/review-bugbot`

Mark it **pending user invocation** until evidence is returned. Record Bugbot as passed, failed, blocked, not run, or not applicable. Tie that status to the reviewed revision and working-tree state.

Remote Bugbot depends on actual repository and pull-request settings. Do not promise remote execution, deduplication, or billing behavior. `validate-change` records Bugbot status from evidence the developer supplies or from checks that are actually visible. It does not merge, and it does not infer a result that was not observed.
