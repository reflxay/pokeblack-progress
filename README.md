# pokeblack progress

Public progress showcase for the private Pokémon Black matching decompilation. Plain HTML, CSS and JavaScript, hosted for free on GitHub Pages at https://reflxay.github.io/pokeblack-progress/.

Inspired by [BFBB's progress site](https://bfbbdecomp.github.io/bfbb/). The layout and interface are original; no BFBB source or assets are copied. The main title uses Korataki Bold with vector outlines and metallic gradients inspired by Pokémon Black's logo.

## Preview

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000. No package installation or frontend build is needed. Fonts are self-hosted: Korataki Bold for both title treatments and the supplied Pokémon Black/White text font for the interface, with system fallbacks for source symbols and addresses. The main title is font-based SVG with layered borders and a dark metallic face, without a bitmap logo.

The main page uses a Pokémon Black 1 battle-menu theme with rectangular panels and buttons, checkered interiors, and layered borders. The previous Black 2-inspired design is preserved at `black2.html` with its own `black2.css`. Click the small Poké Ball at the far right of either page's footer to switch designs. Both pages share the same live progress snapshot and function explorer.

## Automatic progress updates

GitHub Actions in the private decompilation repo runs on each push to `main`. It rebuilds ARM9 and ARM7, exports `data/progress.json`, and pushes only that snapshot to this public repo. GitHub Pages then deploys the updated site. No PC task or local updater is used.

The private repo needs an Actions secret named `PROGRESS_SITE_TOKEN`. Use a fine-grained token that can access only `reflxay/pokeblack-progress`, with **Contents: read and write**, then add it under the private repo's **Settings → Secrets and variables → Actions**. The workflow keeps producing its private report artifact without this token, but it cannot publish the site until the secret is configured. Run the existing `report` workflow once from the Actions page after adding the secret to publish the current main revision; later pushes update the site automatically.

Each published revision is the exact private `main` commit. The main branch is advanced only after the lead's full ROM comparison; the Actions build also checks the ARM9 and ARM7 hashes before publishing. Only `data/progress.json` is copied to the public repo. It contains progress metadata, not source code or game assets.

## Metrics

Code percentage is matching C function-sized bytes divided by tracked code bytes, measured with objdiff v3.8.0 across linked ARM9, autoloads, and overlays. The exporter only includes functions present in the linker map. Assembly ranges can include embedded literal pools. ARM7, data-only regions, assets and discarded helper functions do not count toward this percentage.

Named-function counts use original emitted assembly function labels and emitted C functions, rather than the synthetic assembly wrapper functions counted by objdiff. Inline assembly is excluded from matching C. An assembly function's byte size is left unknown instead of estimated from adjacent symbols.

The progress workflow exports the exact private main revision, rechecks the ARM9 and ARM7 binaries against their recorded hashes, and relies on the repository's full-ROM verification gate before main is advanced. Its object configuration, tools and reports stay in the ignored `.cache/` directory.

Only `data/progress.json` contains project-specific public metadata: symbol names, source filenames, module names, addresses, byte counts, the main commit identifier and hash-check results. No private source, ROM, extracted game assets, SDK, compiler, credentials, personal paths or raw logs are published.
