# Release-Readiness Triage Agent

## Problem

Release go/no-go decisions get made on whatever evidence happens to be
present. Nobody systematically checks what evidence should exist and
is missing. A pull request (PR) touches a subsystem; the test that
should cover that subsystem either ran or nobody noticed it didn't.
This tool's job is to name the absence, not summarize the presence.

It runs against one repo (ArduPilot), one release range at a time
(e.g. the merges between two release tags), and one hand-written
mapping of code paths to the test paths that should cover them.

## The three evidence inputs

For each PR in the range that touches a mapped subsystem, the agent
looks at three things, all pulled from the GitHub API:

1. **Which files changed in the diff.** Checked against the
   subsystem's code paths (did this PR touch the subsystem) and its
   test paths (did the same PR also touch a file under the mapped
   test directory).
2. **The PR body text.** Checked for a ticked testing checkbox
   (ArduPilot's PR template has three: automated test, tested
   manually, tested on hardware) or prose describing verification. The
   claim is quoted verbatim if found. It is never scored or verified.
3. **Whether the commit resolves to a real, reviewed PR at all.**
   ArduPilot's stable release branches route every commit through a
   small number of release-bookkeeping PRs that bundle ~90 already
   reviewed changes into one batch. This tool does not trust that
   direct lookup; it searches the rest of the repo's history for the
   commit's real originating PR instead, and reports "unresolved"
   rather than guess when that search is ambiguous or comes up empty.

**CI check-run status is explicitly not one of the three inputs.** It
was tried and dropped. Checked against 5 real PRs that touched the
same subsystem: all five ran the same suite of roughly 90 CI jobs, all
green, every time. The job names are keyed to hardware target or
vehicle type (`build (stm32h7)`, `sitltest-copter-tests1a`), never to
which part of the code was touched. A gap defined as "no matching CI
job ran" would report zero gaps on all five PRs, which is a null
result, not a finding. See `docs/LEARNINGS.md` #1 for the full writeup.

## What the buckets mean

Each PR that touches a mapped subsystem lands in one of three named
buckets, plus a separate category for commits that can't be resolved
to a PR at all:

1. **No test, no claim.** The PR touched the subsystem, no file under
   the mapped test path is in the same diff, and the PR body has no
   testing checkbox ticked and no testing prose.
2. **Claimed, not evidenced.** No test file in the diff, but the PR
   body ticks a testing checkbox or describes verification in prose.
   The claim is quoted, never scored. This bucket is explicitly not
   called "tested": a claim is not evidence the tool has checked, and
   the label says so.
3. **Test present.** A file under the mapped test path is in the same
   diff as the subsystem change.
4. **Unresolved.** The commit landed on the release branch but no
   identifiable reviewed PR could be found for it, only the
   release-bookkeeping batch. The review trail itself is a gap here,
   separate from any subsystem's test coverage.

Report order is gaps first: bucket 1, then bucket 2, then unresolved
commits, then bucket 3 last as supporting detail.

## The gate rule

Every run ends in a GO / NO-GO verdict, and that verdict is plain,
deterministic code, never derived from anything a language model
writes (there is no LLM in this tool at all right now, but the rule
would hold if one were ever added: it could write summary prose after
the verdict, never produce the verdict itself).

The verdict keys on exactly two inputs, and only these two, because
each one can structurally produce a failing result:

- bucket 1 count (a subsystem change with no test and no claim)
- unresolved commit count (no identifiable reviewed PR)

A PR body claim (bucket 2) does not gate the verdict. It can only ever
soften a no-test result into something less bad; it can never
independently fail one, since the tool never verifies whether the
claim is true. An input that can only ever say "maybe fine" and never
"no" is not evidence for a pass/fail gate, so it doesn't get to vote.
The report states this next to the verdict every time, not just here.

## How to run it

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GITHUB_TOKEN
python data_layer.py [base_tag] [head_tag]
```

Both tags are optional positional arguments; omitted, they default to
`Copter-4.7.0 Copter-4.7.1`. Each run prints a terminal report and also
writes `reports/<base_tag>_to_<head_tag>.md`. The subsystem-to-test
mapping is hand-maintained in `config/subsystems.yaml`, not inferred.

## What it found

The tool was run against 8 real tag-pair ranges: the original
Copter-4.7.0 to 4.7.1 verification range, plus point-release pairs for
Copter, ArduPlane, and Rover. Because ArduPilot is one monorepo,
several of those tag pairs turned out to bracket nearly the same
underlying commits across vehicles, so the 8 ranges reduce to 4
genuinely distinct commit windows (see `reports/SWEEP.md` for the full
breakdown and the counting caveat).

**Bucket 1 fired in 3 of those 4 distinct commit windows.** One of the
flagged PRs: **#27799**, `AP_GPS: Backport correct satellite count for
SBF DNU NrSv value`, merged into the Copter-4.5 branch with no test
file in its diff and no testing claim in its body. It was reverted
about two weeks later, folded into the next release-bookkeeping PR,
after a user on the ArduPilot forum reported that on affected
Septentrio GPS units the change caused a bad or missing HDOP reading
to come through as `0.0`, which reads as ideal GPS quality rather than
bad, so the failsafe check that should trigger on poor HDOP never saw
a bad value. A fail-open in a failsafe check.

## What it does not do

- It does not read PR labels, review comments, or review approvals.
- It does not read CI logs or check-run status at all (see above).
- It does not judge whether a claimed test is credible, or whether a
  test file present in the diff actually covers the change. Both of
  those judgments are left to the human reader.
- **It would not have found the #27799 bug itself.** The HDOP-to-zero
  failure mode was only surfaced by real-world field testing reported
  on a forum, not by anything this tool checks. All this tool would
  show, then or now, is that the PR shipped with no test file and no
  claim in its body: an absence of re-runnable evidence, not a defect
  finding. Naming that absence is the entire scope of the tool.

## Further reading

- `docs/LEARNINGS.md`: five cases where this tool's first design would
  have printed a confident, wrong answer, and what changed each time.
- `reports/SWEEP.md`: the full 8-range sweep, including the
  same-commit-window caveat and the deduplicated bucket counts.
- `docs/PRD.md`: original scope and design, with a note pointing back
  to `SWEEP.md`/`STATE.md` for current state.
