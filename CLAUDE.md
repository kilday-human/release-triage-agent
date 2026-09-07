# CLAUDE.md

Release-readiness triage agent: reads signals about a release (PRs, issues,
CI, etc.) and produces a go/no-go style triage output. See docs/PRD.md for
scope, docs/STATE.md for current status (STATE.md is authoritative over
memory).

## Commands
- Activate venv: `source venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run tests: `pytest`

## Rules

1. Double-check every claim before stating it. At the end of any response
   with factual claims, give a table: claim | how verified.
2. Never state something as fact that you have not checked yourself. If you
   did not verify it, say so explicitly instead of guessing.
3. No em-dashes in any prose written for Christopher.
4. No inflated or unverifiable claims in READMEs or docs. Any number must
   carry its qualifier (source, date, or method), not stand alone.
5. `.env` is gitignored, never hardcode `GITHUB_TOKEN` or any secret in
   code, docs, or commit history. This repo goes public before Demo Day.
