# Sweep: 8 ranges, 4 distinct commit windows

Gate logic and bucket definitions unchanged for this run - see
`docs/LEARNINGS.md` and `data_layer.py` for what they are. This is a
measurement-only pass: same code, more ranges.

**Read the counts with this caveat first:** ArduPilot is one monorepo.
Copter, Plane, and Rover point releases at the same version number
(e.g. `*-4.6.1` -> `*-4.6.2`) are frequently cut from nearly the same
point in shared history. Two trios below are confirmed byte-identical
in commit count, PR count, and every bucket assignment across all
three vehicles - they are one underlying commit window measured three
times, not three independent samples. Rows are grouped by window below
so this isn't silently averaged away.

## Results

| Window | Range | Commits | Resolved PRs | Unresolved | Bucket 1 | Bucket 2 | Bucket 3 | Verdict |
|---|---|---|---|---|---|---|---|---|
| D | Copter-4.7.0 -> Copter-4.7.1 | 94 | 29 | 0 | 0 | 2 | 1 | GO |
| C | Copter-4.5.6 -> Copter-4.5.7 | 42 | 23 | 1 | 2 | 0 | 0 | NO-GO |
| A | Copter-4.6.1 -> Copter-4.6.2 | 121 | 47 | 0 | 1 | 1 | 0 | NO-GO |
| A | Plane-4.6.1 -> Plane-4.6.2 | 121 | 47 | 0 | 1 | 1 | 0 | NO-GO |
| A | Rover-4.6.1 -> Rover-4.6.2 | 121 | 47 | 0 | 1 | 1 | 0 | NO-GO |
| B | Copter-4.6.2 -> Copter-4.6.3 | 146 | 70 | 0 | 2 | 0 | 0 | NO-GO |
| B | Plane-4.6.2 -> Plane-4.6.3 | 145 | 69 | 0 | 2 | 0 | 0 | NO-GO |
| B | Rover-4.6.2 -> Rover-4.6.3 | 145 | 69 | 0 | 2 | 0 | 0 | NO-GO |

Window A's three rows all resolved to the identical PR set: bucket 1 =
PR #30306, bucket 2 = PR #29905. Window B's three rows all resolved to
the identical PR set: bucket 1 = PR #30873 and PR #30946 (the small
145-vs-146 commit-count difference is a per-vehicle version-bump commit,
not a bucket result).

**Deduplicated by distinct window (the honest denominator): 4 windows,
not 8.**

| Window | Bucket 1 | Bucket 2 | Bucket 3 |
|---|---|---|---|
| D (Copter-4.7.0/1) | 0 | 2 | 1 |
| C (Copter-4.5.6/7) | 2 | 0 | 0 |
| A (4.6.1/2, all 3 vehicles) | 1 | 1 | 0 |
| B (4.6.2/3, all 3 vehicles) | 2 | 0 | 0 |
| **Total (4 windows)** | **5** | **3** | **1** |

## Answers

**Did bucket 1 ever fire? Which range, which PR?**
Yes, in 3 of the 4 distinct windows (not window D, the original
verification range). First occurrence: window A (Copter-4.6.1 ->
Copter-4.6.2, also Plane and Rover's identical range), PR #30306,
`AP_GPS: cope with F9P configured to never send MSG_STATUS` - a GPS
code change with no test file in its diff and no testing claim in its
body. Window B added PR #30873 and PR #30946, both GPS. Window C
(Copter-4.5.6 -> Copter-4.5.7) added PR #27799 (GPS, a direct PR) and
PR #28328 - a release-bookkeeping PR that only lands in bucket 1
because one specific commit fallback-attributed to it (a revert of
the same backport as #27799, `AP_GPS: revert backport ... satellite
count for NrSv`) directly touches `libraries/AP_GPS/AP_GPS_SBF.cpp`
with no PR of its own. Checked by hand against the commit's own file
list, not just trusted from the pipeline - this is the LEARNINGS #3/#4
fix working as designed, not a new bug.

**Bucket 2 to bucket 3 ratio across all ranges.**
By distinct window (the number that means anything): 3 bucket-2
results to 1 bucket-3 result. By raw report row (8 rows, counting
window A and B three times each): 5 to 1 - a bigger-looking number
that's mostly the same 2 windows counted twice extra each. The
deduplicated 3:1 is the one to use; all of bucket 3's single occurrence
and most of bucket 2's total come from window D, the only window
sampled so far where a subsystem change shipped with its test file in
the same diff.

**Do Plane and Rover differ from Copter?**
No difference observed in windows A and B - but that's because those
two windows are, for these three vehicles, the same commits, not
because Plane/Rover engineering practice matches Copter's. This sample
gives zero evidence either way about cross-vehicle difference; it only
shows the tag pairs chosen happened to bracket shared history. A real
answer would need windows where the vehicles' tag cuts diverge instead
of coincide.
