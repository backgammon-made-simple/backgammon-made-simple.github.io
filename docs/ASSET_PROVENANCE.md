# Website Asset Provenance and Regeneration

## Approved brand sources

The approved project-owned favicon and app-icon sources are retained in `favicons_logos_icons/`. They entered the repository before this task and were normalized to that path in commit `5c75b59`. The 2026-07-22 website context identifies this directory as the approved source and directs that the files be integrated without redrawing, resizing, recolouring, or destructive renaming.

The public copies are byte-for-byte copies in `site/assets/icons/`. The web manifest was corrected only to use the deployed `/assets/icons/` paths.

| Public file | Dimensions/format | SHA-256 |
|---|---|---|
| `apple-touch-icon.png` | 180×180 PNG | `3CC88E3C0F068E8CD1DB4FA404E05881AEA7A60D50ABF9137FEABA6B2FC07498` |
| `favicon-96x96.png` | 96×96 PNG | `589B3A102F1B6094ED7020C8E556D3C69892A6F79C2BA7FCD6AA00C5DE2F1BA1` |
| `favicon.ico` | 16×16 ICO | `CD77C221134A79F218124159A025895275ECC17242B1B98D7DF2B4A42F409D21` |
| `favicon.svg` | SVG | `FFBC66D7B5DDE16FB4ACB1D8B348A83F2CC415FDF44723F93F36450151B21B32` |
| `web-app-manifest-192x192.png` | 192×192 PNG | `1D963A64265183EF4A0365325A0C01C3197AF11998F28C8B924A615950A8561C` |
| `web-app-manifest-512x512.png` | 512×512 PNG | `E07359CE7AB15D11E1712F7E442B00082D91F0E3A45E997191DDF16187F4F4C3` |

The active site logo, `site/assets/logo.svg`, is the approved `favicons_logos_icons/logo-clean.svg` file byte-for-byte (SHA-256 `F088025AB8E60FF0FF8677C8997FEBE3CD25283360B9E0FE013ADE85DD32E585`). Project licensing does not grant trademark rights in these brand assets.

## Social previews

The canonical build command is:

```powershell
quarto render site
```

The Quarto pre-render hook runs:

```powershell
python social_generator/scripts/social/run_social_pipeline.py
```

That command uses the existing contract-v1.1 text-only renderer, local Source Sans 3 fonts, the approved site logo, and the current homepage metadata. It refreshes `site/assets/social/social-cards.yml`, validates the manifest and page relationships, renders changed cards, and validates the PNG dimensions before Quarto renders.

| Generated file | Dimensions | SHA-256 |
|---|---:|---|
| `site/assets/social/generated/social-default.png` | 1200×630 | `42444DD0C956F1B5BE2C0492F1BDF04B8DF92E10CC3651171818692199609BC2` |
| `site/assets/social/generated/github-backgammon-made-simple.png` | 1280×640 | `5BEBE6FD66B12E8F375F5B59A65FBF19EBC9D3A9A436A7ED2263E90DCE1F334C` |

Generation is deterministic for the pinned Python packages, installed Chromium version, renderer/templates, font files, logo, and metadata recorded in the manifest. The `.render-state.json` file records content hashes used for changed-card builds.

## Font evidence

The social renderer uses unmodified Source Sans 3 Regular and SemiBold TTF files. Their embedded metadata reports version 3.052 and Adobe copyright. The exact-release upstream source is <https://github.com/adobe-fonts/source-sans/tree/3.052R>, licensed under the SIL Open Font License 1.1. The exact-release licence file is stored as `LICENSES/OFL-1.1.txt`.

## Licence text evidence

| Local file | Authoritative source | SHA-256 |
|---|---|---|
| `LICENSES/AGPL-3.0-only.txt` | <https://www.gnu.org/licenses/agpl-3.0.txt> | `0D96A4FF68AD6D4B6F1F30F713B18D5184912BA8DD389F86AA7710DB079ABCB0` |
| `LICENSES/CC-BY-SA-4.0.txt` | <https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt> | `28A9529C7D0BB4DC51F4BF5C116A3D16EF247A052F7591466768DDF563FD1CF5` |
| `LICENSES/OFL-1.1.txt` | <https://raw.githubusercontent.com/adobe-fonts/source-sans/3.052R/LICENSE.md> | `89AD2C4F66DD29127527493E729C31E731F111CF10FAF5774C3DB9275ED0C22C` |

## Old-site comparison

The old website contains a different `site/assets/logo.svg` (SHA-256 `276DBD3BA21204AEC7422D6C148827BF947984FA0635E333173AB8093857018E`). It remains reference-only. The current approved logo and icon set were not replaced by old-site assets.
