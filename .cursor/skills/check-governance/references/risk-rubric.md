# Risk rubric

Routine checks cover repository instructions, changed paths, test evidence, and external-write approval.

Recommend deeper analysis for changes involving:

- authentication, authorization, IAM, secrets, or permissions;
- personal, financial, regulated, or integrity-sensitive data;
- irreversible migration, deletion, or externally visible behavior;
- infrastructure, production boundaries, unfamiliar dependencies, or high uncertainty.

Do not regenerate BUGBOT.md during each review. Propose an update only when observed repository invariants or recurring bug risks make the existing guidance materially stale.
