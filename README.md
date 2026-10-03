# pokeblack progress

Public progress showcase for the private Pokémon Black matching decompilation. Plain HTML, CSS and JavaScript, hosted for free on GitHub Pages at https://reflxay.github.io/pokeblack-progress/.

Inspired by [BFBB's progress site](https://bfbbdecomp.github.io/bfbb/). The implementation and artwork here are original; no BFBB source or assets are copied.

## Preview

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000. No package installation or frontend build is needed. Fonts use Google Fonts with local system fallbacks.

## Update progress

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

GitHub Pages rebuilds after a push to this site's main branch. The private decompilation repo is not accessed by the browser or the public website workflow. Snapshot updates are intentionally published from verified local builds; a private source token is not stored in this repository.

## Metrics

Code percentage is matching C function-sized bytes divided by tracked code bytes, measured with objdiff v3.8.0 across linked ARM9, autoloads, and overlays. The exporter only includes functions present in the linker map. Assembly ranges can include embedded literal pools. ARM7, data-only regions, assets and discarded helper functions do not count toward this percentage.

Named-function counts use original emitted assembly function labels and emitted C functions, rather than the synthetic assembly wrapper functions counted by objdiff. Inline assembly is excluded from matching C. An assembly function's byte size is left unknown instead of estimated from adjacent symbols.

Export requires a successful integration receipt for the exact clean main revision and independently checks ARM9, ARM7 embedded in the final ROM, and the whole ROM against the repository's reference hashes. The exporter never modifies the decompilation checkout. Its local object configuration, tools and reports stay in the ignored `.cache/` directory.

Only `data/progress.json` contains project-specific public metadata: symbol names, source filenames, module names, addresses, byte counts, the main commit identifier and hash-check results. No private source, ROM, game assets, SDK, compiler, credentials, personal paths or raw logs are published.
