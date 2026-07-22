# Backgammon Made Simple

**Questions players ask. Ideas you can use.**

Backgammon Made Simple is a free, open-source, question-driven learning project built around real positions, engine evidence, and practical mental models players can use at the board.

This repository contains the public website and its website-specific analysis services.

## Website development

See [docs/authoring-guide.md](docs/authoring-guide.md) for the site structure,
authoring conventions, local preview commands, and route map.


## What lives here

- The Quarto website and Learn curriculum
- Blog posts and educational content
- The R Shiny position analyzer
- The website-specific Python worker
- Direct worker access and support for an external bridge
- Static assets, build tooling, validation, and deployment configuration

Reusable engine models and wrappers belong in [`backgammon-engine-kit`](https://github.com/backgammon-made-simple/backgammon-engine-kit). Scientific engine-versus-engine studies belong in [`backgammon-engine-benchmarks`](https://github.com/backgammon-made-simple/backgammon-engine-benchmarks).

## Product structure

- **Learn** teaches ideas through real questions and positions.
- **Analyze** applies those ideas to positions supplied by readers.
- **Sage vs GNU** creates interesting engine comparisons and feeds durable questions back into Learn.
- **Blog** holds research notes, position breakdowns, project updates, and material that is not yet part of the permanent curriculum.

The central learning progression is:

```text
Question → position → decision → explanation → mental model
```

## Project values

Backgammon Made Simple is a passion project and a public record of the long process of learning to understand the game more deeply.

Use it. Study it. Improve it. Adapt it. Even build a business with it—but credit the project and keep covered improvements open.

That principle is implemented through copyleft licensing:

- software improvements stay open under the **GNU AGPL v3**;
- adaptations of educational material stay open under **CC BY-SA 4.0**.

## Repository layout

The exact layout may evolve. Preserve the current working `site/`, `shiny/position-dashboard/`, favicon assets, and `social_generator/` paths until migration parity is proven:

```text
site/                 Quarto website and educational content
app/ or shiny/        R Shiny analyzer
worker/               Website-specific Python worker
scripts/              Build, validation, migration, and maintenance tools
assets/               Website assets and educational diagrams
```

See [`LICENSE.md`](LICENSE.md) for the authoritative license mapping.

## Development status

This project is under active development. Interfaces, routes, analysis formats, and curriculum structure may change before a stable release.

## Local development

The canonical website build is:

```powershell
quarto render site
```

Quarto's pre-render hook refreshes and validates the social-card manifest, validates the existing text-only renderer, generates changed PNGs, and checks their dimensions before the site render begins. To run that pipeline directly:

```powershell
python social_generator/scripts/social/run_social_pipeline.py
```

With the rendered `_site` directory served locally, run the metadata and keyboard smoke test with:

```powershell
python social_generator/scripts/social/check_rendered_site.py <local-preview-url>
```

Install its pinned Python dependencies from `social_generator/requirements-social.txt`, install Chromium with `python -m playwright install chromium`, and install the R `yaml` package listed in `social_generator/requirements-social.R`.

A typical development workflow also requires:

- Quarto
- R and the required R packages
- Python 3.11 or newer
- access to the configured analysis worker
- any external engine dependencies documented by `backgammon-engine-kit`

Do not commit private credentials, deployment secrets, or third-party engine files that cannot be redistributed.

## Source access

The analyzer and other network-facing software are licensed under AGPL-3.0-only. Any modified version offered to users over a network must provide those users with access to the corresponding source code as required by that license.

The official project source is:

<https://github.com/backgammon-made-simple/backgammon-made-simple.github.io>

## Contributing

Corrections, clearer explanations, reproducible positions, bug reports, and code improvements are welcome.

Contributions should:

- preserve the question-driven educational approach;
- distinguish engine evidence from interpretation;
- identify third-party material and its license;
- avoid implying endorsement by an engine, platform, author, or federation;
- follow the repository's licensing and attribution rules.

A fuller `CONTRIBUTING.md` will define the review process as the project matures.

## Licensing

This is a mixed-license repository:

- **Software:** AGPL-3.0-only
- **Educational content:** CC BY-SA 4.0
- **BMS name, logo, and distinctive official branding:** no trademark rights granted
- **Third-party material:** remains under its original license

See [`LICENSE.md`](LICENSE.md) for details.

## Disclaimer

Engine analysis is evidence, not infallible proof. Backgammon evaluations depend on position encoding, match context, analysis settings, software versions, and methodology. Educational material should make assumptions and uncertainty clear.
