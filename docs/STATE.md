# STATE

This file is authoritative over anything Claude remembers. Update it every session.

## Current status
Data layer works, report generation works. Verified against
`Copter-4.7.0` → `Copter-4.7.1` (94 commits, 29 resolved PRs, 0
unresolved): 3 results, each individually hand-checked against GitHub,
not just trusted from the pipeline's own output. Rerun after adding
report generation reproduced the same 94/29/0 exactly, no drift.
Repo is on GitHub, private, pushed:
https://github.com/kilday-human/release-triage-agent. No README yet,
no CLI wrapper (run directly via `python data_layer.py`). One run now
produces both a terminal report and a saved markdown file at
`reports/<base-tag>_to_<head-tag>.md`.

Report order: bucket 1 (no test, no claim), bucket 2 ("claimed, not
evidenced" - relabeled from "no test, claim stated" so a claim is
never presented as a test), unresolved commits, bucket 3 (test
present). Verdict (GO/NO-GO) is deterministic code in `gate_verdict()`
- gates only on bucket-1 count and unresolved count, the two inputs
that can structurally produce a failing result. Bucket 2 (PR body
claims) is flagged in the report itself (`NON_GATING_NOTE`) as
non-evidence: it can only ever soften a no-test result, never
independently fail one, since the tool never verifies the claim text.
No LLM is wired in anywhere in this repo yet - nothing currently
writes summary prose, so there's nothing to gate against LLM-derived
verdicts, but the rule (verdict is code-only, LLM if ever added may
only add prose after the verdict is fixed) is now written into the
code's own docstring for whoever adds that next.

Bucket 2 claim text is now extracted and quoted verbatim
(`get_claim()`), not just flagged as a boolean - checkbox label text
first, falling back to the first matching prose line. If a bucket-2
result somehow has no extractable claim, the report prints `MISSING`
rather than inferring or leaving it blank.

## Last session
2026-09-28: Measurement-run session, gate logic and bucket definitions
untouched throughout.

- Step 1: `BASE_TAG`/`HEAD_TAG` are now CLI args (`python data_layer.py
  [base_tag] [head_tag]`, default unchanged). Reran the default range
  after the plumbing change: still 94 commits, 29 resolved PRs, 0
  unresolved - exact match, confirmed before moving on.
- Step 2: swept 8 ranges total into `reports/` - the original
  Copter-4.7.0/4.7.1, two more Copter point releases (4.6.1/4.6.2,
  4.6.2/4.6.3), one older Copter window (4.5.6/4.5.7, added mid-session
  in place of the 4.5.7->4.6.0 minor-version boundary, which at 3918
  commits wasn't comparable to the point releases), and matching
  4.6.1/4.6.2 and 4.6.2/4.6.3 pairs for Plane and Rover.
- Step 3: `reports/SWEEP.md` written. Key finding: the two 4.6.x trios
  across Copter/Plane/Rover are byte-identical in commits, PRs, and
  bucket assignments - one monorepo, same underlying commit window cut
  three times. 8 report rows = 4 distinct windows. Deduplicated
  bucket2:bucket3 is 3:1, not the raw 5:1. Bucket 1 fired for the first
  time this project: PR #30306 (window A), PR #30873/#30946 (window
  B), PR #27799 and PR #28328 (window C, Copter-4.5.6/4.5.7 -
  #28328's bucket-1 result checked by hand: a real GPS revert commit
  with no PR of its own, correctly restricted to its own file per the
  LEARNINGS #3/#4 fix, not the bookkeeping PR's full bundle).
- Step 4: hand-check pointers given - bucket 2 example PR #29905
  (GPS, claim quoted, not verified), bucket 3 example PR #33947
  (Loiter, only bucket-3 result in the whole sweep so far).
- New false-confidence failure logged as LEARNINGS #5: sweeping
  multiple tag-pair ranges in a monorepo doesn't give independent
  samples when the vehicles' tags bracket the same underlying history.
  Caught before shipping the ratio, not after.
- Two transient GitHub API 500s during the sweep, both cleared on
  retry - infrastructure flakiness, not a code or logic issue.

## Next up
- README, written for someone outside the project
- The Plane-vs-Rover-vs-Copter question is still open. Windows A and B
  happened to be identical commit sets across vehicles - need a range
  where the vehicles' tag cuts actually diverge to get a real answer.
- Bucket 3 is now confirmed to be genuinely rare across measured
  ranges (1 occurrence in 4 distinct windows) - may be worth reframing
  the demo around bucket 1 vs bucket 2 (real gap vs. unverified claim)
  rather than waiting for more bucket-3 hits
