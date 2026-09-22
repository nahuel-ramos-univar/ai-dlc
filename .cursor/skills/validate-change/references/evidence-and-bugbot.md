# Evidence and Bugbot

Evidence identifies the checked revision, uncommitted state, command or inspection performed, result, and acceptance criterion covered. A test command that did not run is unavailable, not passed.

`validate-change` owns Bugbot coordination. This plugin cannot invoke Bugbot programmatically. When Bugbot is required or requested, ask the developer to run:

`/review-bugbot`

Mark it **pending user invocation** until evidence is returned. Record Bugbot as passed, failed, blocked, not run, or not applicable. Tie that status to the reviewed revision and working-tree state.

Remote Bugbot depends on actual repository and pull-request settings. Do not promise remote execution, deduplication, or billing behavior. `deliver-change` may inspect configured checks but must not coordinate or infer Bugbot results.
