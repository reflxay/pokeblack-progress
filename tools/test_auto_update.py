"""Small runnable checks for receipt identity and safe retry of snapshot-only commits."""
import tempfile
from pathlib import Path

from auto_update import COMMIT_PREFIX, pending_snapshots, receipt_for
from export_progress import MATCH_LINES, git


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    receipt = root / "tasks/example/integration.md"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("integrated_commit: " + "a" * 40 + "\nbase_main: " + "b" * 40 +
                       "\n" + "\n".join(MATCH_LINES))
    assert receipt_for(root, "a" * 40) == receipt
    assert receipt_for(root, "b" * 40) is None
    receipt.write_text(receipt.read_text().replace(MATCH_LINES[-1], "ROM mismatch"))
    assert receipt_for(root, "a" * 40) is None
    compare_log = receipt.parent / "integration-compare.log"
    receipt.write_text("verified_main: " + "a" * 40 + "\ncompare_log: " +
                       str(root / "old-checkout" / compare_log.name) + "\n")
    assert receipt_for(root, "a" * 40) is None
    compare_log.write_text("\n".join(MATCH_LINES))
    assert receipt_for(root, "a" * 40) == receipt
    assert receipt_for(root, "b" * 40) is None
    compare_log.write_text("\n".join(MATCH_LINES[:-1]) + "\nROM mismatch")
    assert receipt_for(root, "a" * 40) is None
    shared_log = root / "integration-compare.log"
    shared_log.write_text("\n".join(MATCH_LINES))
    receipt.write_text("verified_main: " + "a" * 40 + "\ncompare_log: " + str(shared_log) + "\n")
    assert receipt_for(root, "a" * 40) == receipt
    shared_log.write_text("\n".join(MATCH_LINES[:-1]) + "\nROM mismatch")
    assert receipt_for(root, "a" * 40) is None
    site = root / "site"
    site.mkdir()
    git(site, "init", "-b", "main")
    git(site, "config", "user.name", "Test")
    git(site, "config", "user.email", "test@example.invalid")
    snapshot = site / "data/progress.json"
    snapshot.parent.mkdir()
    snapshot.write_text("{}")
    git(site, "add", ".")
    git(site, "commit", "-m", "Initial snapshot")
    git(site, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert not pending_snapshots(site)
    snapshot.write_text('{"revision":"new"}')
    git(site, "add", ".")
    git(site, "commit", "-m", COMMIT_PREFIX)
    assert pending_snapshots(site)
    (site / "other.txt").write_text("Unrelated work must not be pushed automatically.")
    git(site, "add", ".")
    git(site, "commit", "-m", COMMIT_PREFIX)
    try:
        pending_snapshots(site)
    except ValueError:
        pass
    else:
        raise AssertionError("Updater accepted an unrelated pending commit")
print("Automatic update checks passed")
