# Step 9 — Reviewer Workflow & Blind Context Fix

A hostile review found the first A/B packets were not strong enough for fair trend labeling and could accidentally include an observation timestamp after the packet `as_of`.

This is fixed.

Each packet now contains a bounded context window where every observation satisfies:

`observation_time <= target as_of`

while System State, Decision Output and future outcomes remain hidden.

Use:
- `labeling/review-ui/labeler-A.html`
- `labeling/review-ui/labeler-B.html`

AI shadow labels exist only for workflow rehearsal and explicitly do not count as human validation.

Human validation remains PENDING until two independent human reviewers submit all packets.
