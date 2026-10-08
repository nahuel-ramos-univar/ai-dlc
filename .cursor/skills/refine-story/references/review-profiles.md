# Refinement review profiles

Use **fast** review for isolated, reversible changes with clear acceptance criteria and known code paths. The main chat may skip independent refinement review. Say why. A documented fast skip is complete.

Use **standard** review when behavior, contracts, regression coverage, or cross-component dependencies may change. Request an independent `refinement-reviewer` assessment.

Use **deep** review for authentication, authorization, payments, data integrity, public contracts, migrations, infrastructure, sensitive data, or substantial uncertainty. Request independent review and identify policy concerns and required approvals. Dedicated governance integration is deferred.

When standard or deep review cannot run, required review stays pending. That does not authorize publication, and the main chat's own refinement is not an independent review. Do not invent a policy exception.

Risk comes from semantic impact, uncertainty, and blast radius. It does not come from file count, file extension, or document format alone.
