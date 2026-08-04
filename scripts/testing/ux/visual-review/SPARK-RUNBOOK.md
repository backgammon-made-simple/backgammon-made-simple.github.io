# Spark visual-review operator runbook

Use this runbook with the task-specific handoff. Do not create another browser,
screenshot, manifest, validator, or gallery framework. The canonical build and
quality procedures remain `scripts/testing/TESTING-SOP.md` and
`scripts/testing/ux/UX-TESTING-SOP.md`.

## 1. Set paths and confirm checkpoints

Run in PowerShell. Replace the four expected values with the exact values in
the task handoff.

```powershell
$WebsiteRepo = 'C:\Users\andre\Documents\backgammon-made-simple.github.io'
$TaskRepo = 'C:\Users\andre\Documents\task-management'
$TaskOutput = Join-Path $TaskRepo 'milestones\developer-tooling\codex-prompts\s016\visual-review'
$ExpectedWebsiteBranch = '<website branch from handoff>'
$ExpectedWebsiteCommit = '<website commit from handoff>'
$ExpectedTaskBranch = '<task-management branch from handoff>'
$ExpectedTaskCommit = '<task-management commit from handoff>'

if ((git -C $WebsiteRepo branch --show-current) -ne $ExpectedWebsiteBranch) { throw 'Unexpected website branch' }
if ((git -C $WebsiteRepo rev-parse HEAD) -ne $ExpectedWebsiteCommit) { throw 'Unexpected website commit' }
if (git -C $WebsiteRepo status --porcelain) { throw 'Website worktree is not clean' }
if ((git -C $TaskRepo branch --show-current) -ne $ExpectedTaskBranch) { throw 'Unexpected task-management branch' }
if ((git -C $TaskRepo rev-parse HEAD) -ne $ExpectedTaskCommit) { throw 'Unexpected task-management commit' }
if (git -C $TaskRepo status --porcelain) { throw 'Task-management worktree is not clean' }
foreach ($Path in @(
  "$WebsiteRepo\scripts\testing\quick.sh",
  "$WebsiteRepo\scripts\testing\comprehensive.sh",
  "$WebsiteRepo\scripts\preview-site.sh",
  "$WebsiteRepo\scripts\testing\ux\browser\release_ui_browser_check.mjs",
  "$WebsiteRepo\scripts\testing\ux\browser\ui_release_manifest.json",
  "$TaskOutput\manifest.json",
  "$TaskOutput\index.html"
)) { if (-not (Test-Path -LiteralPath $Path)) { throw "Missing required path: $Path" } }
```

Stop on any mismatch or unexplained change. Do not reset, clean, or switch
branches to conceal it.

## 2. Build and run automation

Run the focused contracts first, then the canonical comprehensive gate. The
comprehensive gate rebuilds `site/_site` and runs the static and rendered-site
checks. Do not run Quarto renders concurrently.

```powershell
Set-Location $WebsiteRepo
& .\.venv\Scripts\python.exe tests\test_release_ui_checks.py
node tests\test_release_ui_browser_check.mjs
bash scripts/testing/quick.sh
bash scripts/testing/comprehensive.sh
& .\.venv\Scripts\python.exe scripts\testing\build\release_ui_static_check.py
git diff --check
```

Use the established browser helper in
`scripts/testing/ux/browser/release_ui_browser_check.mjs` for static, release,
interaction, horizontal-overflow, clipping, changed-control overlap, console,
and keyboard-focus evidence. Follow `scripts/testing/ux/UX-TESTING-SOP.md` for
fresh navigation, continuous-content loading, real keyboard traversal, report
interpretation, and isolation. A browser report that finds a product defect is
completed evidence, not an automatic pass.

## 3. Start the fixed preview

Run this in a dedicated terminal and leave it running during capture:

```powershell
Set-Location $WebsiteRepo
bash scripts/preview-site.sh 8765
```

The only capture origin is `http://127.0.0.1:8765/`. In another terminal:

```powershell
(Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8765/').StatusCode
```

Require status `200`. Do not capture against a different port, commit, build,
or server process.

## 4. Select manifest pairs and capture with the in-app browser

The task manifest is `$TaskOutput\manifest.json`. Treat each pair's route,
viewport, state, requested scroll position, interaction steps, screenshot path,
and diagnostics as the capture contract. Use the existing Codex in-app browser
and its viewport screenshot API; do not install or invoke another screenshot
framework.

For an affected-only refresh, list the exact IDs in the task handoff:

```powershell
$AffectedIds = @('<exact pair id from handoff>')
$VisualManifest = Get-Content "$TaskOutput\manifest.json" -Raw | ConvertFrom-Json
$CapturePairs = @($VisualManifest.pairs | Where-Object id -In $AffectedIds)
if ($CapturePairs.Count -ne $AffectedIds.Count) { throw 'An affected pair ID is missing from the manifest' }
$CapturePairs | Select-Object id,route,state,@{n='viewport';e={"$($_.viewport.width)x$($_.viewport.height)"}},after_screenshot
```

Use this exact Spark browser directive for each selected pair:

```text
Use the existing Codex in-app browser at http://127.0.0.1:8765/. Start from a
fresh navigation to the manifest route, set the exact manifest viewport, and
perform interaction_steps.after in order. For continuous content, wait for the
documented ready and append state before settling the requested scroll Y.
Exercise focus with real keyboard input. Capture a viewport screenshot, not a
full-page screenshot, to the manifest after_screenshot path. Record actual
scroll Y, document/content/visual-viewport widths, viewport-intersecting clipped
controls, changed-control overlaps, and console errors. Do not capture any pair
whose ID is not explicitly selected. Reset the viewport after the batch.
```

Before every interaction, take a fresh DOM snapshot and require a unique
target. Reload the canonical route between states. Keep before evidence
unchanged unless the handoff explicitly authorizes a new before build.

The browser bridge has a five-minute control-call ceiling. Preserve manifest
order and split work into deterministic sequential batches of at most six pairs:

```powershell
$BatchSize = 6
for ($Start = 0; $Start -lt $CapturePairs.Count; $Start += $BatchSize) {
  $End = [Math]::Min($Start + $BatchSize - 1, $CapturePairs.Count - 1)
  ,$CapturePairs[$Start..$End] | Select-Object -ExpandProperty id
}
```

Do not run batches concurrently. A batch must use the same commit, rendered
output, server, manifest, browser, and viewport definitions. If a batch times
out, restart that whole batch from a fresh route state; never splice ambiguous
browser state into accepted evidence.

## 5. Validate every pair and dimension

After updating the selected after screenshots and the manifest diagnostics,
run this against all pairs, not only the refreshed subset:

```powershell
Add-Type -AssemblyName System.Drawing
$VisualManifest = Get-Content "$TaskOutput\manifest.json" -Raw | ConvertFrom-Json
if ($VisualManifest.methodology.final_visual_status -ne 'PENDING MARTY REVIEW') { throw 'Final visual status changed' }
if (@($VisualManifest.pairs).Count -ne 36) { throw 'Expected 36 screenshot pairs' }
if (@($VisualManifest.pairs.id | Sort-Object -Unique).Count -ne @($VisualManifest.pairs).Count) { throw 'Duplicate pair ID' }
foreach ($Pair in $VisualManifest.pairs) {
  if ($Pair.visual_review_status -ne 'PENDING MARTY REVIEW' -or -not $Pair.human_review_pending) { throw "Invalid review status: $($Pair.id)" }
  $BeforePath = Join-Path $TaskOutput $Pair.before_screenshot
  $AfterPath = Join-Path $TaskOutput $Pair.after_screenshot
  if (-not (Test-Path -LiteralPath $BeforePath) -or -not (Test-Path -LiteralPath $AfterPath)) { throw "Missing screenshot: $($Pair.id)" }
  $Before = [System.Drawing.Image]::FromFile($BeforePath)
  $After = [System.Drawing.Image]::FromFile($AfterPath)
  try {
    if ($Before.Width -ne $After.Width -or $Before.Height -ne $After.Height) { throw "Dimension mismatch: $($Pair.id)" }
    if (-not $Pair.scroll_position.aligned -or -not $Pair.interaction_steps.identical) { throw "Unaligned pair contract: $($Pair.id)" }
  } finally { $Before.Dispose(); $After.Dispose() }
}
```

Any missing pair, dimension mismatch, unaligned route/state/scroll contract,
new overflow, clipping, overlap, console, focus, or interaction finding blocks
handoff until it is explained.

## 6. Assemble and validate the continuous gallery

The established gallery is `$TaskOutput\index.html`. Its existing renderer
maps the embedded `pairs` array into one scrolling document; do not replace that
renderer. After manifest pair metadata changes, synchronize only that embedded
array:

```powershell
@'
const fs = require('fs');
const path = require('path');
const root = process.argv[2];
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const indexPath = path.join(root, 'index.html');
const html = fs.readFileSync(indexPath, 'utf8');
const next = html.replace(/    const pairs = \[[\s\S]*?\];\r?\n    const gallery =/, `    const pairs = ${JSON.stringify(manifest.pairs)};\n    const gallery =`);
if (next === html) throw new Error('Gallery pairs marker was not found');
fs.writeFileSync(indexPath, next, 'utf8');
'@ | node - $TaskOutput
```

Validate all stable IDs, hash links, pair counts, image links, and pending
statuses by executing the gallery's real script against a minimal document:

```powershell
@'
const fs = require('fs');
const path = require('path');
const root = process.argv[2];
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) throw new Error('Gallery script missing');
const gallery = { innerHTML: '' };
new Function('document', scriptMatch[1])({ getElementById: id => id === 'gallery' ? gallery : null });
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const cardIds = [...gallery.innerHTML.matchAll(/<article id="([^"]+)" class="card review-pair">/g)].map(match => match[1]);
const linkIds = [...gallery.innerHTML.matchAll(/<a class="pair-id" href="#([^"]+)">#([^<]+)<\/a>/g)];
if (cardIds.length !== manifest.pairs.length || new Set(cardIds).size !== cardIds.length) throw new Error('Gallery card IDs invalid');
if (!cardIds.every((id, index) => id === manifest.pairs[index].id)) throw new Error('Gallery IDs do not match manifest order');
if (linkIds.length !== cardIds.length || !linkIds.every((match, index) => match[1] === cardIds[index] && match[2] === cardIds[index])) throw new Error('Stable hash links invalid');
for (const pair of manifest.pairs) {
  if (!gallery.innerHTML.includes(pair.before_screenshot) || !gallery.innerHTML.includes(pair.after_screenshot)) throw new Error(`Gallery screenshot missing: ${pair.id}`);
}
if ((gallery.innerHTML.match(/PENDING MARTY REVIEW/g) || []).length !== cardIds.length) throw new Error('Pending statuses invalid');
console.log(`Validated ${cardIds.length} stable gallery IDs and screenshot pairs.`);
'@ | node - $TaskOutput

git -C $WebsiteRepo diff --check
git -C $TaskRepo diff --check
```

## 7. Stop and report

Stop `scripts/preview-site.sh` with `Ctrl-C` in its dedicated terminal. Confirm
that port 8765 is no longer reachable. Report:

- exact branches and commits tested;
- exact commands and focused pair IDs;
- tests and browser checks passed, failed, or not run;
- every detected finding without suppressing it;
- `$TaskOutput\manifest.json`;
- `$TaskOutput\index.html`;
- every refreshed screenshot path;
- final status `PENDING MARTY REVIEW`.

Spark may make a small focused UI correction, run these established commands,
use the existing in-app browser and manifest, refresh explicitly affected
screenshots, assemble and validate the existing gallery, and make routine
focused commits.

Spark must stop when the testing framework itself is broken, browser state is
nondeterministic, shared navigation or layout architecture requires redesign,
the expected branches or commits do not match, a stable regression has an
unclear cause, or the fix would broaden the requested scope.
