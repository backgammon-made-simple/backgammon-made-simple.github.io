# Text-Only Social Card Amendment

The project owner has directed that the social-card renderer be text-only.

The frozen nine-field manifest shape remains unchanged. The required `visual`
field is retained for schema compatibility, but the only valid value in the
text-only renderer is:

```yaml
visual: ""
```

The renderer no longer implements or silently ignores the earlier `board`,
`cube`, `analysis`, or `benchmark` presets. A nonempty `visual` value is a fatal
validation error.

All differences among `default`, `github`, `section`, `article`, `tool`, and
`benchmark` cards are expressed through typography, spacing, rule weight,
content width, and composition. No generated illustrations, preset SVGs,
decorative background images, or visual fallback rules are used.

This is the one intentional semantic change from the frozen v1.0 contract.
The remaining schema, dimensions, output mappings, validation order, security,
local-asset, screenshot, page-integration, and post-render requirements remain
in force.
