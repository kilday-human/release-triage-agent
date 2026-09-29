"""
Data layer for the release-readiness triage agent.

Fetches PRs in a release range from GitHub, then classifies each
subsystem touch into one of three buckets using only string/regex
operations on data already pulled - no LLM in the gating path.
See docs/PRD.md "Processing" for why CI check-run status was dropped
and why this classification exists instead.

Commit-to-PR resolution does NOT trust direct lookup on this repo.
Verified across the whole range: every commit on the stable release
branch resolves directly to one of a small number of umbrella
"beta/official release" batch PRs (e.g. #34030, #34225 for
Copter-4.7.1), which bundle ~90 already-reviewed changes - their body
and checkboxes describe the release process, not any individual
change's own test coverage. The real originating PR is found instead
by matching commit message against the rest of the repo's history,
falling back to the direct/umbrella PR only when no more specific
match exists. An ambiguous or absent match is reported as
"unresolved", not guessed - see resolve_by_message().
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

GITHUB_API = "https://api.github.com"
REPO = "ArduPilot/ardupilot"
BASE_TAG = "Copter-4.7.0"
HEAD_TAG = "Copter-4.7.1"
CACHE_PATH = Path(".cache/pr_resolution.json")

TESTING_CHECKBOX_LABELS = (
    "automated test",
    "tested manually",
    "tested on hardware",
)
CLAIM_KEYWORDS = (
    "autotest",
    "sitl",
    "replay",
    "bench",
    "hardware",
    "verified",
    "tested",
)

CHECKBOX_LINE = re.compile(r"^- \[([ xX])\]\s*(.+)$", re.MULTILINE)
BOILERPLATE_HEADING = re.compile(
    r"^#{1,6}\s*(Summary|Description|Classification\s*&\s*Testing.*)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


class GitHubClient:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        })

    def get(self, path):
        resp = self.session.get(f"{GITHUB_API}{path}")
        resp.raise_for_status()
        return resp.json()

    def get_paginated(self, path):
        results = []
        page = 1
        while True:
            resp = self.session.get(
                f"{GITHUB_API}{path}",
                params={"page": page, "per_page": 100},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return results

    def search_commits(self, query):
        """Search API has its own, tighter rate limit. Back off on 403
        with X-RateLimit-Remaining: 0 instead of failing the run."""
        while True:
            resp = self.session.get(
                f"{GITHUB_API}/search/commits",
                params={"q": query},
            )
            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - time.time(), 1) + 1
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("items", [])


def load_subsystems(path="config/subsystems.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)["subsystems"]


def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def commits_in_range(client, repo, base, head):
    data = client.get(f"/repos/{repo}/compare/{base}...{head}")
    return [(c["sha"], c["commit"]["message"]) for c in data["commits"]]


def first_line(message):
    return message.split("\n")[0].strip()


def resolve_by_message(client, repo, sha, message, cache):
    """Finds OTHER commits in the repo with an identical first message
    line (excluding this commit's own SHA) and resolves each to its own
    PR. This exists because direct commit->PR lookup on this repo's
    stable release branch resolves EVERY commit to one of a small
    number of umbrella "beta/official release" batch PRs (verified
    across the whole range, not just cherry-picked spot checks) - those
    PRs bundle ~90 already-reviewed changes, so their body/checkboxes
    describe the release process, not any individual change's test
    coverage. The real originating PR (where a testing claim, if any,
    would actually be written) is found by message match against the
    rest of the repo's history. Returns pr=None with ambiguous=False
    when no other commit shares the message (the umbrella PR is then
    genuinely the only answer - true for version-bump/release-note
    commits). Ambiguous or unresolvable results are never guessed."""
    key = f"{repo}:{sha}"
    if key in cache:
        return cache[key]

    target = first_line(message)
    query = f'repo:{repo} "{target}"'
    items = client.search_commits(query)

    candidate_prs = set()
    for item in items:
        if item["sha"] == sha:
            continue
        if first_line(item["commit"]["message"]) != target:
            continue
        for pr in client.get(f"/repos/{repo}/commits/{item['sha']}/pulls"):
            candidate_prs.add(pr["number"])

    if len(candidate_prs) == 0:
        result = {"pr": None, "ambiguous": False, "reason": None}
    elif len(candidate_prs) == 1:
        result = {"pr": next(iter(candidate_prs)), "ambiguous": False, "reason": None}
    else:
        result = {
            "pr": None,
            "ambiguous": True,
            "reason": f"ambiguous: candidate PRs {sorted(candidate_prs)}",
        }

    cache[key] = result
    save_cache(cache)
    return result


def resolve_prs(client, repo, commits, cache):
    """Returns (prs_by_number, commits_by_pr, fallback_prs, unresolved).
    For each commit, prefers a more specific PR found via message match
    over this repo's direct lookup (which always resolves to an
    umbrella release PR here - see resolve_by_message). Falls back to
    the direct/umbrella PR only when no more specific alternative
    exists. Ambiguous message matches, and commits with no PR at all,
    are reported as unresolved rather than guessed - the review trail
    couldn't be identified, which is itself a gap to report.

    commits_by_pr tracks which of THIS RANGE's commits are actually
    attributed to each PR. fallback_prs marks PRs that were only ever
    reached through the fallback branch - i.e. message matching found
    no more specific PR for any commit attributed to them. That's the
    structural definition of a batch/umbrella PR here, not a file-count
    threshold: a threshold would misclassify a large legitimate PR and
    miss a small batch one. classify_range uses this to restrict a
    batch PR's evaluation to only its attributed commits' own files,
    instead of the batch PR's entire unrelated diff."""
    prs_by_number = {}
    commits_by_pr = {}
    fallback_prs = set()
    unresolved = []

    for sha, message in commits:
        own = {pr["number"]: pr for pr in client.get(f"/repos/{repo}/commits/{sha}/pulls")}
        result = resolve_by_message(client, repo, sha, message, cache)

        if result["ambiguous"]:
            unresolved.append({
                "sha": sha,
                "message": first_line(message),
                "reason": result["reason"],
            })
            continue

        if result["pr"] is not None:
            number = result["pr"]
            if number not in prs_by_number:
                prs_by_number[number] = own.get(number) or client.get(f"/repos/{repo}/pulls/{number}")
            commits_by_pr.setdefault(number, []).append(sha)
            continue

        if own:
            prs_by_number.update(own)
            fallback_prs.update(own.keys())
            for number in own:
                commits_by_pr.setdefault(number, []).append(sha)
        else:
            unresolved.append({
                "sha": sha,
                "message": first_line(message),
                "reason": "no PR found via direct lookup or message match",
            })

    return prs_by_number, commits_by_pr, fallback_prs, unresolved


def pr_files(client, repo, number):
    return [
        f["filename"]
        for f in client.get_paginated(f"/repos/{repo}/pulls/{number}/files")
    ]


def commit_files(client, repo, sha):
    data = client.get(f"/repos/{repo}/commits/{sha}")
    return [f["filename"] for f in data.get("files", [])]


def touches_any(filenames, prefixes):
    return any(f.startswith(p) for f in filenames for p in prefixes)


def strip_boilerplate(body):
    """Remove template checkbox lines and section headings so keyword
    search below only sees actual prose, not the ArduPilot PR template's
    own boilerplate (which contains words like "test" and "hardware"
    whether or not the box is ticked)."""
    text = CHECKBOX_LINE.sub("", body)
    text = BOILERPLATE_HEADING.sub("", text)
    return text


def ticked_checkbox_labels(body):
    return [
        label.strip()
        for mark, label in CHECKBOX_LINE.findall(body)
        if mark.lower() == "x" and any(kw in label.lower() for kw in TESTING_CHECKBOX_LABELS)
    ]


def prose_claim_lines(body):
    text = strip_boilerplate(body)
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and any(kw in line.lower() for kw in CLAIM_KEYWORDS)
    ]


def get_claim(body):
    """Returns {"source", "text"} with the verbatim claim (checkbox label(s)
    or first matching prose line), or None if no claim is present. Never
    scores or verifies the claim - see PRD 'Processing', bucket 2: the tool
    reports the claim, the human judges it."""
    labels = ticked_checkbox_labels(body)
    if labels:
        return {"source": "checkbox", "text": "; ".join(labels)}
    prose = prose_claim_lines(body)
    if prose:
        return {"source": "prose", "text": prose[0]}
    return None


def bucket_for_subsystem(files, claim, subsystem):
    """Returns None if this PR doesn't touch the subsystem, else 1/2/3."""
    if not touches_any(files, subsystem["code_paths"]):
        return None
    if touches_any(files, subsystem["test_paths"]):
        return 3
    if claim is not None:
        return 2
    return 1


def classify_range(client, subsystems, cache):
    commits = commits_in_range(client, REPO, BASE_TAG, HEAD_TAG)
    prs, commits_by_pr, fallback_prs, unresolved = resolve_prs(client, REPO, commits, cache)

    results = []
    for number, pr in sorted(prs.items()):
        if number in fallback_prs:
            # Batch/umbrella PR: reached only through fallback, meaning
            # message matching found no more specific PR for any commit
            # attributed to it. Its own diff and body describe the
            # release process, not any one attributed commit, so
            # restrict to only the files of commits actually attributed
            # to it in this range, and never trust its body as a claim.
            files = set()
            for sha in commits_by_pr.get(number, []):
                files.update(commit_files(client, REPO, sha))
            files = list(files)
            body = ""
        else:
            files = pr_files(client, REPO, number)
            body = pr.get("body") or ""

        claim = get_claim(body)
        for subsystem in subsystems:
            bucket = bucket_for_subsystem(files, claim, subsystem)
            if bucket is not None:
                results.append({
                    "pr": number,
                    "title": pr["title"],
                    "subsystem": subsystem["name"],
                    "bucket": bucket,
                    "claim": claim if bucket == 2 else None,
                })

    for u in unresolved:
        files = commit_files(client, REPO, u["sha"])
        u["subsystems_touched"] = [
            s["name"] for s in subsystems if touches_any(files, s["code_paths"])
        ]

    return len(commits), len(prs), results, unresolved


BUCKET_LABELS = {
    1: "No test, no claim",
    2: "Claimed, not evidenced",
    3: "Test present",
}

# Gate rule: an input only gates the verdict if it can structurally
# produce a failing result. Test-file-in-diff (bucket 1 vs 3) and
# commit->PR resolution (unresolved) both can. A PR body claim (bucket 2)
# can only ever soften a no-test result, never independently fail one -
# the tool never verifies it (see PRD "Processing") - so it's flagged
# here as non-evidence instead of silently counted toward the verdict.
NON_GATING_NOTE = (
    'PR body claims (bucket 2, "claimed, not evidenced") are quoted for '
    "context only. The tool does not verify them, so this input can "
    "never independently produce a failing result and does not affect "
    "the verdict above."
)


def gate_verdict(bucket1_count, unresolved_count):
    """Deterministic, code-only verdict - never derived from LLM output.
    Gates only on inputs that can say no: bucket 1 (subsystem change,
    no test, no claim) and unresolved commits (no identifiable reviewed
    PR). See NON_GATING_NOTE for why bucket 2 is excluded."""
    reasons = []
    if bucket1_count:
        reasons.append(f"{bucket1_count} subsystem change(s) with no test and no claim")
    if unresolved_count:
        reasons.append(f"{unresolved_count} commit(s) with no identifiable reviewed PR")
    verdict = "NO-GO" if reasons else "GO"
    return verdict, reasons


def build_report_data(commit_count, pr_count, results, unresolved):
    by_bucket = {1: [], 2: [], 3: []}
    for r in results:
        by_bucket[r["bucket"]].append(r)
    verdict, reasons = gate_verdict(len(by_bucket[1]), len(unresolved))
    return {
        "commit_count": commit_count,
        "pr_count": pr_count,
        "unresolved": unresolved,
        "by_bucket": by_bucket,
        "verdict": verdict,
        "reasons": reasons,
    }


def claim_text(r):
    claim = r.get("claim")
    return claim["text"] if claim else "MISSING"


def print_report(data):
    print(f"Release range: {BASE_TAG} -> {HEAD_TAG} "
          f"({data['commit_count']} commits, {data['pr_count']} resolved PRs, "
          f"{len(data['unresolved'])} unresolved commits)\n")

    print(f"Verdict: {data['verdict']}")
    for reason in data["reasons"]:
        print(f"  - {reason}")
    if not data["reasons"]:
        print("  - no bucket 1 gaps, no unresolved commits")
    print()
    print(f"Note: {NON_GATING_NOTE}\n")

    for bucket in (1, 2):
        rows = data["by_bucket"][bucket]
        print(f"== Bucket {bucket}: {BUCKET_LABELS[bucket]} ({len(rows)}) ==")
        for r in rows:
            print(f"  PR #{r['pr']} [{r['subsystem']}] {r['title']}")
            if bucket == 2:
                print(f'      claim: "{claim_text(r)}"')
        print()

    unresolved = data["unresolved"]
    print(f"== Unresolved: commit landed, no identifiable reviewed PR ({len(unresolved)}) ==")
    for u in unresolved:
        touched = f" [touches: {', '.join(u['subsystems_touched'])}]" if u["subsystems_touched"] else ""
        print(f"  {u['sha'][:9]} {u['message']}{touched}  ({u['reason']})")
    print()

    rows = data["by_bucket"][3]
    print(f"== Bucket 3: {BUCKET_LABELS[3]} ({len(rows)}) ==")
    for r in rows:
        print(f"  PR #{r['pr']} [{r['subsystem']}] {r['title']}")
    print()


def render_markdown(data):
    lines = [f"# Release triage: {BASE_TAG} -> {HEAD_TAG}", ""]
    lines.append(
        f"{data['commit_count']} commits, {data['pr_count']} resolved PRs, "
        f"{len(data['unresolved'])} unresolved commits."
    )
    lines.append("")
    lines.append(f"## Verdict: {data['verdict']}")
    lines.append("")
    if data["reasons"]:
        for reason in data["reasons"]:
            lines.append(f"- {reason}")
    else:
        lines.append("- no bucket 1 gaps, no unresolved commits")
    lines.append("")
    lines.append(f"> {NON_GATING_NOTE}")
    lines.append("")

    def bucket_section(bucket):
        rows = data["by_bucket"][bucket]
        out = [f"## Bucket {bucket}: {BUCKET_LABELS[bucket]} ({len(rows)})", ""]
        if not rows:
            out.append("_none_")
        for r in rows:
            out.append(f"- PR #{r['pr']} [{r['subsystem']}] {r['title']}")
            if bucket == 2:
                out.append(f'  - claim: "{claim_text(r)}"')
        out.append("")
        return out

    lines += bucket_section(1)
    lines += bucket_section(2)

    unresolved = data["unresolved"]
    lines.append(f"## Unresolved: commit landed, no identifiable reviewed PR ({len(unresolved)})")
    lines.append("")
    if not unresolved:
        lines.append("_none_")
    for u in unresolved:
        touched = f" [touches: {', '.join(u['subsystems_touched'])}]" if u["subsystems_touched"] else ""
        lines.append(f"- `{u['sha'][:9]}` {u['message']}{touched} ({u['reason']})")
    lines.append("")

    lines += bucket_section(3)

    return "\n".join(lines)


def report_filename():
    return f"{BASE_TAG}_to_{HEAD_TAG}.md"


def main():
    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    client = GitHubClient(token)
    subsystems = load_subsystems()
    cache = load_cache()
    commit_count, pr_count, results, unresolved = classify_range(client, subsystems, cache)
    data = build_report_data(commit_count, pr_count, results, unresolved)

    print_report(data)

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename()
    report_path.write_text(render_markdown(data))
    print(f"Saved: {report_path}")


if __name__ == "__main__":
    main()
