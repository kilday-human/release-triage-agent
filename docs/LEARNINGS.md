# LEARNINGS

This tool checks whether a software release has the test evidence it
should. Given a range of changes going into a release (a set of pull
requests, or "PRs" - a proposed code change plus its review discussion,
on GitHub), it sorts each one into a bucket: did the change include a
test, did the author at least say how they verified it, or is there
neither. The idea is to name what's missing, not just list what ran.

This is the log of what broke while building it. Each entry is a case
where the tool's first design would have printed a confident, wrong
answer - not crashed, not returned nothing, just quietly told the
wrong story. The point of keeping this log is that none of these
failures were obvious from the outside. Each one looked like working
software until we checked it against real data. That pattern is worth
recording as its own finding, not just the four individual bugs, so
the log closes with it.

---

## 1. CI status is not evidence of anything subsystem-specific

**Assumed:** if a change touched a subsystem (say, the flight
controller's navigation filter) and the project's CI system - the
automated build-and-test suite that runs on every PR - showed no test
job for that subsystem, that absence was a real gap.

**What the data showed:** we checked five real PRs that touched the
navigation filter. All five ran the exact same suite of roughly 90
jobs, and all five came back green. The job names were things like
"build (stm32h7)" and "autotest (sitltest-copter-tests1a)" - keyed to
which hardware target or vehicle type was being built, never to which
part of the code was touched. There is no job named after the
subsystem, so there is no absence to detect.

**What the wrong version would have shipped:** a report claiming zero
gaps across all five PRs, presented as "full test coverage." The
number would have been technically computed correctly from the data
available. It just measured nothing.

**What changed:** dropped CI job status entirely as a signal. Replaced
it with something checkable from the PR itself: does the same PR that
changes the subsystem's code also change a file in the project's test
directory. That's a real, checkable split - three of the five PRs had
one, two didn't.

---

## 2. Looking up "which PR introduced this change" pointed at the wrong PR

**Assumed:** GitHub can tell you, for any given commit (a single
saved change, identified by a unique ID called a SHA), which PR it
came from. We assumed that lookup was reliable.

**What the data showed:** on this project's stable release branch,
every single commit we checked - not a handful, the whole range -
resolved to one of exactly two PRs, both of which were just "cut the
release" bookkeeping PRs that bundle around 90 already-reviewed
changes into one batch. The lookup wasn't returning nothing; it was
confidently returning an answer, and the answer was always the
shipping paperwork, never the PR where the actual change was written,
reviewed, and (maybe) tested.

**Why this is worse than a null result:** a null result looks like a
gap in your data and gets noticed. This looked like a complete,
specific answer - "PR #34030, here's its title" - which makes it easy
to trust and move on. The tool would have read that bookkeeping PR's
description, found no mention of testing this specific change (because
the description is about the release, not the change), and called it
a gap. Evidence about a totally different subject was being credited,
or blamed, on the wrong change.

**What changed:** added a second lookup - search the rest of the
project's history for another commit with the identical message, and
resolve that one to its PR instead. If that search finds nothing else,
the original bookkeeping PR really is the only answer (true for things
like version-number bump commits, which never have a separate PR). If
the search turns up more than one plausible original PR, the commit is
marked "unresolved" - the review trail couldn't be identified - rather
than guessed. Every lookup is cached to disk so re-running the check
doesn't repeat the same searches.

---

## 3. The bookkeeping PR's full change-list was still being read as one thing

**Assumed:** once a commit was correctly traced back to a bookkeeping
PR (because no better answer existed, per finding 2), it was safe to
check that PR's full list of changed files against our subsystems.

**What the data showed:** a bookkeeping PR that bundles 90 changes
touches well over a hundred files in total. Three of those files
happened to belong to the navigation filter, GPS, and one flight mode
- but those specific changes were different commits, already correctly
traced to their own real PRs (#33730, #33904, #33947) via finding 2's
fix. The bookkeeping PR got credited with touching those subsystems
anyway, because we were still reading its entire file list as if it
were one change instead of ~90 stapled together.

**What the wrong version would have shipped:** three fabricated
results, reporting the bookkeeping PR - not the real PR - as the
source of changes to the navigation filter, GPS, and flight mode,
double-counting work that had already been correctly attributed
elsewhere.

**What changed:** when a commit only resolves to a bookkeeping PR
(finding 2's fallback path), the check now looks only at that specific
commit's own small set of changed files, not the bookkeeping PR's
entire bundle. The bookkeeping PR's own description is also no longer
trusted as evidence of testing for any individual change - it's
release notes, not a test report.

---

## 4. The first fix for #3 didn't actually fix anything

**Assumed:** a good way to tell a "bookkeeping, bundles everything"
PR apart from a normal one is to count how many files it changed, and
treat anything over a threshold as bulk.

**What the data showed:** the fix was applied, the code ran, and the
output was byte-for-byte identical to the broken version - same three
fabricated results, unchanged. The file-count field the check relied
on simply wasn't present on the lightweight PR record returned by this
particular lookup (a different, smaller data shape than the one used
elsewhere in the same tool). Reading a missing field silently returns
zero, zero is under any reasonable threshold, so the check that was
supposed to catch bulk PRs never once fired.

**Why this is worse than it sounds:** this wasn't caught by an error
message. It was caught by comparing two runs and noticing the numbers
hadn't moved when they should have. A file-count threshold is also
wrong in principle even when it works: it would misjudge a large,
genuine, single-purpose PR as bulk, and miss a small bookkeeping PR
that happened to bundle only a few changes.

**What changed:** dropped the file-count idea entirely. "Bookkeeping"
is now defined by how the PR was found, not by its size: if a commit
only ever resolved to a PR through finding 2's fallback path - meaning
no more specific original PR could be found for it - that PR is
treated as bookkeeping for that commit, full stop. That's a fact about
the lookup, not a guess based on a number.

---

## The pattern across all four

Every one of these produced output that looked like a real, specific
answer. None of them crashed, timed out, or came back empty in a way
that would prompt a second look. Each was only caught by checking the
tool's output against the real, underlying data by hand, one small
case at a time, before trusting anything it said.

The tool exists to catch quiet absences - changes that shipped without
the evidence they should have had. Building it, we kept independently
rediscovering the same lesson from the inside: a tool can manufacture
evidence that isn't there just as easily as a release process can, and
it will do it confidently, in a format that looks exactly like a real
finding.
