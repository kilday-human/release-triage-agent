# STATE

This file is authoritative over anything Claude remembers. Update it every session.

## Current status
Repo scaffolded, baseline committed (8f2e0a3). PRD written and revised
against real ArduPilot data. No application code yet.

## Last session
2026-09-07: PRD interview complete. Validated gap-detection design
against 5 real EKF-touching PRs via `gh api` (#34283, #34194, #34057,
#34188, #34027). Found CI check-run status is a null signal (always
green, job names not subsystem-scoped) and replaced it with a
file-diff + PR-body-checkbox classification into 3 buckets (no
test/no claim, no test/claim stated, test present). Locked release
target to `Copter-4.7.0` → `Copter-4.7.1`.

## Next up
- Write the data-layer script: pull PRs in the Copter-4.7.0→4.7.1
  range (commit→PR resolution, no merge commits since ArduPilot
  squash-merges), classify each into the 3 buckets
- Write the subsystem-to-test mapping config (EKF, GPS, one flight
  mode) as checked-in YAML/JSON
- Confirm requirements.txt deps (PyGithub or raw requests + PyYAML)
