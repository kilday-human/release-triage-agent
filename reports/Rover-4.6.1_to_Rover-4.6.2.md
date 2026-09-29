# Release triage: Rover-4.6.1 -> Rover-4.6.2

121 commits, 47 resolved PRs, 0 unresolved commits.

## Verdict: NO-GO

- 1 subsystem change(s) with no test and no claim

> PR body claims (bucket 2, "claimed, not evidenced") are quoted for context only. The tool does not verify them, so this input can never independently produce a failing result and does not affect the verdict above.

## Bucket 1: No test, no claim (1)

- PR #30306 [GPS] AP_GPS: cope with F9P configured to never send MSG_STATUS

## Bucket 2: Claimed, not evidenced (1)

- PR #29905 [GPS] AP_GPS: DroneCAN: only trust ellipsoid height if different from MSL
  - claim: "Tested on Cube Orange and MatekL431-Periph nodes (running various code versions) connected to a u-blox GPS."

## Unresolved: commit landed, no identifiable reviewed PR (0)

_none_

## Bucket 3: Test present (0)

_none_
