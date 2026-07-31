# Lesson analysis SVG MVP fixture provenance

These assets are retained fixture artifacts. They are not newly verified engine
positions or engine analysis.

## Source repositories

- `backgammonboard` branch `gallery`, commit
  `a4b8188138506d5ca2cfc294092922a45cfe3b34`
- accepted Engine Kit fixture source commit
  `33409334c6f4d6fca0d798ba4a324673e72e86ce`

## Asset mapping

| Website asset | Retained source |
|---|---|
| `starting.svg` | `task-work/B-BR-01/output/gallery/01-accepted-opening-learner-right.svg` |
| `responder-flipped.svg` | `task-work/B-BR-01/runtime/gallery/02-opening-rotated-view.svg` |
| `candidate-1.svg` | `task-work/B-BR-01/output/gallery/06-one-player-on-bar.svg` |
| `candidate-2.svg` | `task-work/B-BR-01/output/gallery/18-late-bearoff.svg` |
| `candidate-3.svg` | `task-work/B-BR-01/output/gallery/10-tall-stacks.svg` |

`starting.svg` and `responder-flipped.svg` have the same retained semantic
state hash:

```text
dccc6114baf3653254eb10ef77b454849be8483227647f73518267035aaa3963
```

The flipped asset comes from an older retained gallery run. The current
`learner-bottom-v1` adapter deliberately rejects rotating the responder to the
bottom. This asset is suitable for testing the website interaction, but a
production responder-perspective workflow requires an explicit
backgammonboard contract decision.

The checker candidate SVGs are representative supplied positions used only to
exercise image replacement and responsive layout. The browser does not apply
moves or infer that these images are legal results of the shared start.

## R rendering attempts

Attempt 1:

```powershell
Rscript -e "setwd('C:/Users/andre/Documents/backgammonboard'); devtools::load_all(...); ..."
```

Result:

```text
Rscript : The term 'Rscript' is not recognized
```

Attempt 2:

```powershell
& 'C:\Program Files\R\R-4.6.1\bin\Rscript.exe' -e 'setwd("C:/Users/andre/Documents/backgammonboard"); ...'
```

Result:

```text
Error: unexpected '/' in "setwd(C:/"
```

Per the task boundary, the same inline method was not retried. The supported
package-level rendering flow remains:

```r
devtools::load_all("C:/Users/andre/Documents/backgammonboard")
position <- renderer_position("path/to/renderer-position.json")
plot <- ggboard(position)
grDevices::svg("position.svg", width = 12, height = 9.1)
print(plot)
grDevices::dev.off()
```
