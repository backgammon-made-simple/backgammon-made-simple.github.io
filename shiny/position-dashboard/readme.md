# Backgammon Made Simple Position Analyzer

A small Shiny app for opening and sharing backgammon positions from an XGID.

Enter an XGID directly or pass one in the URL. The app validates the position and renders it with `bglab`.

## Run locally

From the repository root:

```bash
Rscript -e "shiny::runApp('shiny/position-dashboard')"
```

The required R packages are:

- `shiny`
- `bglab`
- `ggplot2`

## Open a position by URL

Use the `position` query parameter:

```text
?position=<URL-encoded-XGID>
```

Example:

```text
?position=XGID%3D-b----E-D---dDa--c-da---AA%3A0%3A0%3A1%3A53%3A0%3A0%3A0%3A5%3A8
```

The app also accepts the XGID payload without the `XGID=` prefix and adds it automatically.

Stable position links make it possible to open the app directly, embed it in a lesson, or share a position with another player.

## Project direction

The Position Analyzer is being developed as a teaching tool for **Backgammon Made Simple**.

Planned additions include:

- ranked checker plays;
- cube decisions;
- equity and error information;
- selectable move overlays;
- Sage and GNU Backgammon analysis;
- links between lessons, positions, and engine results.

The goal is not only to show the answer, but to help explain the decision.

## Contributing

Bug reports and focused improvements are welcome.

For position-rendering problems, include:

- the XGID or complete URL;
- what you expected to see;
- what appeared instead;
- whether the app was opened directly or embedded.

Please keep changes focused and preserve the existing XGID and `bglab::ggboard()` rendering path unless a renderer change is intentional.

## Backgammon Made Simple

Backgammon Made Simple is an independent educational project about backgammon decisions, positions, cube play, and analysis.

```text
Understand the idea → see it in a position → make a decision → analyze the result
```

## License

See the repository licence files for the software and content terms.

The **Backgammon Made Simple** name, logo, and brand assets are reserved.
