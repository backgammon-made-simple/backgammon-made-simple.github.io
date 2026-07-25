# Research custom-listing render fix

This patch adds:

- `site/research/index.qmd`
- `site/research/_research-listing.ejs.md`

Before rendering, remove the superseded file:

```bash
rm -f site/research/research-listing.ejs.md
```

The leading underscore prevents Quarto from treating the EJS template as a
standalone project render target.
