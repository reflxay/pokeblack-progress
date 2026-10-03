# pokeblack progress

Public progress showcase for the private Pokémon Black matching decompilation. Plain HTML, CSS and JavaScript, hosted for free on GitHub Pages at https://reflxay.github.io/pokeblack-progress/.

Inspired by [BFBB's progress site](https://bfbbdecomp.github.io/bfbb/). The implementation and artwork here are original; no BFBB source or assets are copied.

## Preview

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000. No package installation or frontend build is needed. Fonts use Google Fonts with local system fallbacks.

## Automatic updates on Windows

The local updater checks for new verified main builds every five minutes using Windows Task Scheduler. The PC must be on and the installing user signed in; Codex does not need to stay open. GitHub Pages deploys each published snapshot.

From this website directory, install the task using a native Python's windowless executable:

```powershell
.\tools\install_auto_update.ps1 -Python 'C:\path\to\pythonw.exe'
```

The default source checkout is the sibling `pokeblack-integration` folder. Override it with `-Repo` when needed. Keep objdiff v3.8.0 at `.cache/objdiff-cli.exe` and use the existing Git sign-in for both repositories. No new token or password is stored by this updater.

The task waits for a clean integration checkout, a successful integration receipt naming the exact main revision, and publication of that revision to private origin. It rechecks the ARM9, ARM7 and full-ROM hashes, exports metadata, commits only `data/progress.json`, and pushes to this website's main branch. Unfinished edits and unchanged revisions are skipped. Failed snapshot pushes are retried without rewriting commits; unrelated local website commits require manual publication.

The task is named `pokeblack progress updater`. Its last-run output is saved in the ignored `.cache/auto-update.log`. Pause or resume it in Task Scheduler, or use:

```powershell
Disable-ScheduledTask -TaskName 'pokeblack progress updater'
Enable-ScheduledTask -TaskName 'pokeblack progress updater'
```

Run these checks when changing the updater:

```powershell
python tools/test_auto_update.py
python tools/export_progress.py --check
```

## Manual updates

At a clean integration boundary, run the decompilation's full `make compare` and record the successful main revision in its integration receipt. Use the existing toolchain and build instructions in that private repository. Never export a dirty worker checkout.

Download [objdiff-cli v3.8.0](https://github.com/encounter/objdiff/releases/tag/v3.8.0) to `.cache/objdiff-cli.exe`, then run from this website directory:

```powershell
python tools/export_progress.py --repo ../pokeblack-integration --objdiff .cache/objdiff-cli.exe --receipt /path/to/current/integration.md
python tools/export_progress.py --check
node --check app.js
git add data/progress.json
git commit -m "Update verified decompilation progress"
git push origin main
```

GitHub Pages rebuilds after a push to this site's main branch. The private decompilation repo is not accessed by the browser or the public website workflow. Snapshots are published from verified local builds; a private source token is not stored in this repository.

## Metrics

Code percentage is matching C function-sized bytes divided by tracked code bytes, measured with objdiff v3.8.0 across linked ARM9, autoloads, and overlays. The exporter only includes functions present in the linker map. Assembly ranges can include embedded literal pools. ARM7, data-only regions, assets and discarded helper functions do not count toward this percentage.

Named-function counts use original emitted assembly function labels and emitted C functions, rather than the synthetic assembly wrapper functions counted by objdiff. Inline assembly is excluded from matching C. An assembly function's byte size is left unknown instead of estimated from adjacent symbols.

Export requires a successful integration receipt for the exact clean main revision and independently checks ARM9, ARM7 embedded in the final ROM, and the whole ROM against the repository's reference hashes. The exporter never modifies the decompilation checkout. Its local object configuration, tools and reports stay in the ignored `.cache/` directory.

Only `data/progress.json` contains project-specific public metadata: symbol names, source filenames, module names, addresses, byte counts, the main commit identifier and hash-check results. No private source, ROM, game assets, SDK, compiler, credentials, personal paths or raw logs are published.
