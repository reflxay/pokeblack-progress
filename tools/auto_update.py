"""Publish a new verified local main snapshot; intended for Windows Task Scheduler."""
import argparse
import contextlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from export_progress import export, git, read_receipt, receipt_verifies, validate

SITE = Path(__file__).resolve().parents[1]
SNAPSHOT = "data/progress.json"
COMMIT_PREFIX = "Update verified decompilation progress"


def receipt_for(store, revision):
    for path in sorted(store.glob("tasks/*/integration.md"), reverse=True):
        if receipt_verifies(read_receipt(path), revision):
            return path
    return None


def pending_snapshots(site):
    commits = git(site, "rev-list", "origin/main..HEAD").decode().splitlines()
    for commit in commits:
        paths = git(site, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines()
        title = git(site, "show", "-s", "--format=%s", commit).decode().strip()
        if paths != [SNAPSHOT] or not title.startswith(COMMIT_PREFIX):
            raise ValueError("Local website commits need manual publication; preserving them.")
    return bool(commits)


def update(repo, refresh=False):
    if git(SITE, "branch", "--show-current").strip() != b"main":
        raise ValueError("Website must be on main.")
    if git(SITE, "status", "--porcelain").strip() or git(repo, "status", "--porcelain").strip():
        print("Waiting: website or integration checkout has unfinished edits.")
        return
    revision = git(repo, "rev-parse", "HEAD").decode().strip()
    if revision != git(repo, "rev-parse", "main").decode().strip():
        print("Waiting: integration checkout is not on verified main.")
        return
    for folder, expected in ((SITE, "pokeblack-progress"), (repo, "pokeblack")):
        remote = git(folder, "remote", "get-url", "--push", "origin").decode().strip()
        if remote not in (f"https://github.com/reflxay/{expected}", f"https://github.com/reflxay/{expected}.git"):
            raise ValueError("Unexpected origin; refusing to publish.")
    git(SITE, "fetch", "--quiet", "origin", "main")
    pending = pending_snapshots(SITE)
    # Fast-forward only: never resolve conflicts or overwrite local work automatically.
    git(SITE, "merge", "--ff-only", "origin/main")
    if pending:
        validate(json.loads((SITE / SNAPSHOT).read_text()))
        git(SITE, "push", "origin", "HEAD:main")
        print("Published pending snapshot.")
    previous = json.loads((SITE / SNAPSHOT).read_text())
    if previous["revision"] == revision and not refresh:
        print(f"Unchanged: {revision[:8]} is already published.")
        return
    store = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()) / "codex-coordination"
    receipt = receipt_for(store, revision)
    if receipt is None:
        print("Waiting: no successful integration receipt for this main revision.")
        return
    published = git(repo, "ls-remote", "origin", "refs/heads/main").decode().split()
    if not published or published[0] != revision:
        print("Waiting: verified local main has not been published to private origin.")
        return
    site_head = git(SITE, "rev-parse", "HEAD")
    candidate = SITE / ".cache/next-progress.json"
    export(repo, SITE / ".cache/objdiff-cli.exe", candidate, receipt)
    if site_head != git(SITE, "rev-parse", "HEAD") or git(SITE, "status", "--porcelain").strip():
        raise ValueError("Website changed during export; preserving edits and waiting.")
    candidate.replace(SITE / SNAPSHOT)
    git(SITE, "add", "--", SNAPSHOT)
    git(SITE, "diff", "--cached", "--check")
    git(SITE, "commit", "-m", f"{COMMIT_PREFIX} ({revision[:8]})", "--", SNAPSHOT)
    # A failed push leaves this snapshot commit intact for the next run to retry.
    git(SITE, "push", "origin", "HEAD:main")
    print(f"Published {revision[:8]}; GitHub Pages will deploy the snapshot.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=SITE.parent / "pokeblack-integration")
    parser.add_argument("--refresh", action="store_true", help="refresh the current verified revision once")
    parser.add_argument("--log", type=Path, help="replace the last-run log, without console windows")
    args = parser.parse_args()
    with contextlib.ExitStack() as stack:
        if args.log:
            args.log.parent.mkdir(exist_ok=True)
            log = stack.enter_context(args.log.open("w", encoding="utf-8"))
            stack.enter_context(contextlib.redirect_stdout(log))
            stack.enter_context(contextlib.redirect_stderr(log))
        print(datetime.now(timezone.utc).isoformat())
        try:
            update(args.repo.resolve(), args.refresh)
        except Exception as error:
            print(f"Update failed: {error}")
            if isinstance(error, subprocess.CalledProcessError) and error.output:
                print(error.output.decode("utf-8", "replace"))
            sys.exit(1)
