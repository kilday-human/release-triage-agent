# STATE

This file is authoritative over anything Claude remembers. Update it every session.

## Current status
Data layer (`data_layer.py`) working end to end against real ArduPilot
data: `Copter-4.7.0` → `Copter-4.7.1`, 94 commits, 29 resolved PRs, 0
unresolved. Three subsystem-touch results, each individually verified
against GitHub by hand: 2 in bucket 2 (#33730 GPS, #33904 EKF), 1 in
bucket 3 (#33947 Loiter). No CLI wrapper or saved-markdown report yet
- output is a terminal print only.

## Last session
2026-09-07: Built and hardened the data layer. Two real false-positive
failure modes surfaced and were fixed before any number was reported
as final:

1. Direct commit->PR lookup (`commits/{sha}/pulls`) on this stable
   branch resolves every commit to one of two umbrella release PRs
   (#34030 "beta1 release", #34225 "official release"), never the
   real originating PR - verified across the whole range, not just
   spot-checked. Fixed with commit-message search against the rest of
   the repo (self-excluding), falling back to the direct/umbrella PR
   only when no more specific match exists. Ambiguous matches are
   reported as unresolved, never guessed. Lookups are cached at
   `.cache/pr_resolution.json` (gitignored) so a rerun doesn't re-burn
   the search API's 30/min rate limit.
2. Even after that fix, the umbrella PRs' own large diffs were still
   being evaluated as one coherent change, misattributing test-file
   evidence from unrelated bundled commits to EKF/GPS/Loiter. Fixed by
   detecting "batch" structurally - a PR is batch if it was reached
   only through the fallback path (no commit attributed to it had a
   more specific message match) - not by a file-count threshold, which
   would misclassify a large legitimate PR and miss a small batch one.
   Batch PRs are evaluated using only their attributed commits' own
   files; their body is never trusted as a claim.

Also earlier in the session: validated the gap-detection design
against 5 real EKF PRs, found CI check-run status is a null signal
(always green, job names not subsystem-scoped), and replaced it with
the file-diff + PR-body-checkbox 3-bucket classification documented in
docs/PRD.md.

## Next up
- CLI wrapper: argparse, write the saved markdown report (gaps first,
  3 buckets named, no score) per PRD's Output section - currently only
  a terminal print
- Decide whether to widen past the 3 seed subsystems before Demo Day,
  per PRD's Later section
- Confirm requirements.txt deps stay minimal (requests, PyYAML,
  python-dotenv) as the CLI/report layer gets built
