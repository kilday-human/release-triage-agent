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
- **Mapping:** checked-in YAML/JSON config, 3-4 subsystems to start
  (EKF, GPS, one flight mode). Each entry maps a set of code paths
  (e.g. `libraries/AP_NavEKF3/`) to the CI jobs/tests that should cover
  them. This file is owned knowledge, written and maintained by
  Christopher, not inferred by the agent.

## Inputs

- GitHub PRs for the release branch: files changed, per PR (via GitHub
  API, authenticated with `GITHUB_TOKEN` from `.env`)
- CI check-run status for those PRs (which jobs ran, pass/fail)
- The subsystem-to-test mapping config

## Processing

For each PR touching a mapped subsystem, check whether the
corresponding CI job(s) ran. A touched subsystem with no matching job
run is a gap. A touched subsystem with a job run (pass or fail) is
present evidence.

## Output

CLI run produces two things:

1. Terminal output, human-readable
2. A saved markdown report (the artifact)

**Report structure is gaps-first.** The report opens with what's
missing — subsystems touched with no corresponding test run. Present
evidence (what did run) goes below, as supporting detail. This ordering
is the thesis of the tool, not a style choice: most triage tools open
with a summary of everything that ran, which quietly buries the risk
this agent exists to surface.

## Done for demo

- CLI command run against real ArduPilot PRs on a real release branch
- Produces a saved markdown report, gaps section first
- At least one real, correct gap identified (a PR that touched EKF/GPS/
  the mapped flight mode with no matching CI job run)
- Report is legible standalone, no narration required

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
