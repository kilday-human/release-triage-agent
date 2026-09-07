# STATE

This file is authoritative over anything Claude remembers. Update it every session.

## Current status
Data layer works. Verified against `Copter-4.7.0` → `Copter-4.7.1`
(94 commits, 29 resolved PRs, 0 unresolved): 3 results, each
individually hand-checked against GitHub, not just trusted from the
pipeline's own output. Repo is on GitHub, private, pushed:
https://github.com/kilday-human/release-triage-agent. No README, no
CLI wrapper, no saved-markdown report yet - output is a terminal print
only.

## Last session
2026-09-07: Four false-confidence failures found and fixed this build.
Each would have printed a specific, confident, wrong answer rather than
an obvious blank. Full writeup, written for an outside reader, is in
`docs/LEARNINGS.md` - keep that as the source of truth for these, don't
duplicate the detail here.

## Next up
- README, written for someone outside the project
- Zero bucket-1 results in this range. Either run more ranges to find
  a real one, or reframe the demo around claim-evidence vs
  artifact-evidence (bucket 2 vs bucket 3), since that split is real
  and already demonstrated
- Report generation: gaps first, terminal plus saved markdown, per
  PRD's Output section
