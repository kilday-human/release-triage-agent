# PRD: Release-Readiness Triage Agent

## Problem

Release go/no-go decisions get made on whatever evidence happens to be
present. Nobody systematically checks what evidence *should* exist and
is missing. A PR touches a subsystem; the test that should cover that
subsystem either ran or nobody noticed it didn't. The agent's job is to
name the absence, not summarize the presence.

## User

Christopher, acting as release manager for the demo repo. Secondary
audience: the markdown report itself is the portfolio artifact — shown
to Andreas, Fabian, Yanbing, or a hiring manager. The report has to
stand on its own without a live walkthrough.

## Scope (v1)

One repo, one release branch, one hand-written subsystem-to-test
mapping. Widen later, not now.

- **Repo:** ArduPilot
- **Release branch:** tag `Copter-4.7.1`. PR range is the merges since
  the previous tag, `Copter-4.7.0` (94 commits between the two tags).
  ArduPilot squash-merges, so there are no merge commits to walk — each
  commit in range is resolved to its PR via
  `GET /repos/{owner}/{repo}/commits/{sha}/pulls`.
- **Mapping:** checked-in YAML/JSON config, 3-4 subsystems to start
  (EKF, GPS, one flight mode). Each entry maps a set of code paths
  (e.g. `libraries/AP_NavEKF3/`) to the test paths that should cover
  them (e.g. `Tools/autotest/arducopter.py`). This file is owned
  knowledge, written and maintained by Christopher, not inferred by the
  agent.

## Inputs

- GitHub PRs for the release branch: files changed, per PR, and the PR
  body text (via GitHub API, authenticated with `GITHUB_TOKEN` from
  `.env`)
- The subsystem-to-test mapping config

CI check-run status was explored and dropped as a gap signal — see
Processing below for why.

## Processing

**CI job status is not usable as a gap signal.** Verified against 5
real EKF-touching PRs (#34283, #34194, #34057, #34188, #34027): all
five ran the same ~90-job suite, all green, every time. Job names are
keyed by vehicle/build target (`sitltest-copter-tests1a`, `build
(stm32h7)`), never by subsystem. Defining a gap as "no matching job
ran" would report zero gaps on all five, which is a null result, not a
finding.

**What the same 5 PRs show instead, from file-diff data:** whether a
test file was touched in the same PR as the subsystem change splits
cleanly — 3 of 5 included a test file, 2 did not. That split is real
and checkable without touching CI at all.

So for each PR touching a mapped subsystem, the agent classifies into
three buckets, checked mechanically (regex/string matching over data
already pulled, no LLM judgment call):

1. **No test, no claim** — no file under the mapped test path in the
   PR diff, and the PR body has no testing checkbox ticked
   (ArduPilot's template: `Automated test(s) verify changes`, `Tested
   manually`, `Tested on hardware`, etc.) and no testing prose.
2. **No test, claim stated** — no test file in the diff, but the PR
   body ticks a testing checkbox and/or contains prose describing
   verification (e.g. "walked release tags to verify", bench-log
   replay, SITL run description). The agent reports the claim text
   verbatim. **It does not assess whether the claim is credible or
   sufficient — that judgment stays with the human reader.**
3. **Test present** — a file under the mapped test path is in the same
   diff as the subsystem change.

Real examples from the 5-PR sample: #34194 (parameter-conversion
removal) has no test file and no checkbox ticked, but its body argues
"no autotest depends on any of the removed code" — bucket 2, claim
stated, not verified by the tool. #34188 (comments-only PR) has
`Automated test(s) verify changes` ticked with no test file in diff —
also bucket 2. #34283, #34057, #34027 all have both a test file and a
checkbox/prose claim — bucket 3.

## Output

CLI run produces two things:

1. Terminal output, human-readable
2. A saved markdown report (the artifact)

**Report structure is gaps-first, three buckets, named, no score.**
Bucket 1 (no test, no claim) leads. Bucket 2 (no test, claim stated)
follows, with the claim quoted, not scored. Bucket 3 (test present)
goes last, as supporting detail. This ordering is the thesis of the
tool, not a style choice: most triage tools open with a summary of
everything that ran, which quietly buries the risk this agent exists
to surface.

## Done for demo

- CLI command run against real ArduPilot PRs on the `Copter-4.7.0` →
  `Copter-4.7.1` range
- Produces a saved markdown report, three buckets, gaps first, no score
- At least one PR correctly classified into bucket 1 or bucket 2 (a PR
  that touched a mapped subsystem with no test file in its diff).
  Note: the 5-PR sample used to design the bucket logic was hand-picked
  for EKF activity and found 2 of 5 in bucket 2, zero in bucket 1 — the
  4.7.0→4.7.1 range itself only has 2 EKF-touching commits total, so
  this criterion may need the mapping's other subsystems (GPS, flight
  mode) to be satisfied, not EKF alone. Confirm against the real range
  before treating this as met.
- Report is legible standalone, no narration required

## Caveat on rate claims

The 2-of-5 split above describes 5 hand-picked PRs used to validate the
bucket design, not a measured rate for ArduPilot. Any statement about
how often ArduPilot PRs land without tests must be qualified by which
PRs it was measured against (e.g. "2 of 5 EKF PRs sampled for design
validation" or "N of M PRs in the Copter-4.7.0→4.7.1 range"), never
stated as a bare rate.

## Later (not building now)

- Inferred subsystem-to-test mapping from CI job names/paths, no manual
  config. Guessing on top of guessing — no ground truth to check it
  against, so it's excluded from v1, not because it's hard.
- Additional subsystems / full ArduPilot path coverage
- Additional repos
- Historical run mode (check what was missing on a past release, verify
  against what actually broke)
- Notifications / CI integration (posting the report as a PR comment,
  blocking merge, etc.)
