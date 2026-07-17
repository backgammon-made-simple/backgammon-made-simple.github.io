# Licensing

Copyright © 2026 Marty Gale and contributors.

This repository contains software, educational material, project branding, and possibly third-party material. Different parts of the repository are licensed differently.

This file explains the license scope. Before public release, the repository should also include the complete legal texts in:

```text
LICENSES/AGPL-3.0-only.txt
LICENSES/CC-BY-SA-4.0.txt
```

## 1. Software — GNU AGPL v3

Unless a file states otherwise, original software in this repository is licensed under the **GNU Affero General Public License, version 3 only**:

```text
SPDX-License-Identifier: AGPL-3.0-only
```

This includes, where present:

- R, Python, JavaScript, TypeScript, shell, and other program source code
- the R Shiny analyzer
- the website-specific Python worker
- APIs, bridges, queues, and network-service code
- Quarto extensions and executable build logic
- generators, validators, migration tools, and maintenance scripts
- tests and reusable software components
- deployment code written specifically for this project

The AGPL permits use, modification, redistribution, and commercial use, subject to its terms. Modified covered software made available to users over a network must provide those users an opportunity to receive the corresponding source code.

Canonical license text:

<https://www.gnu.org/licenses/agpl-3.0.html>

## 2. Educational material — CC BY-SA 4.0

Unless a file states otherwise, original educational material is licensed under the **Creative Commons Attribution-ShareAlike 4.0 International License**:

```text
SPDX-License-Identifier: CC-BY-SA-4.0
```

This includes, where present:

- Learn lessons
- Blog articles and research explanations
- curriculum text and teaching notes
- authored position commentary
- original educational diagrams, charts, and illustrations
- explanatory prose in Quarto or Markdown files
- non-software documentation intended primarily as educational content

You may share and adapt this material, including commercially, provided that you:

1. give appropriate credit;
2. provide a link to the license;
3. indicate whether changes were made;
4. distribute adaptations under CC BY-SA 4.0 or a compatible license;
5. do not imply endorsement by Backgammon Made Simple.

Canonical license and legal code:

<https://creativecommons.org/licenses/by-sa/4.0/>

### Recommended attribution

> Based on material from **Backgammon Made Simple** by Marty Gale and contributors.  
> Source: <https://github.com/backgammon-made-simple/backgammon-made-simple.github.io>  
> Licensed under **CC BY-SA 4.0**.  
> Changes were made.

Attribution may be provided in another reasonable form that satisfies the license.

## 3. Mixed Quarto and notebook files

A `.qmd`, `.Rmd`, or notebook may contain both educational prose and executable code.

Use these rules:

- substantial executable code should be moved into a separately licensed source file when practical;
- educational prose is CC BY-SA 4.0;
- substantial original software code is AGPL-3.0-only;
- a file containing both should include a clear notice identifying the license of each portion.

Do not assume that a file extension alone determines the license.

## 4. Name, logo, and official branding

The AGPL and CC BY-SA licenses do **not** grant trademark rights.

The following are not licensed for use as the identity of a fork, course, service, or derivative project:

- the **Backgammon Made Simple** name as an official project identity;
- the BMS logo and favicon;
- distinctive official brand marks and social templates;
- statements implying official status, affiliation, sponsorship, or endorsement.

Forks and adaptations may accurately state that they are based on Backgammon Made Simple and must preserve required attribution. They should use their own name and visual identity.

In plain language:

> Fork the work, not the identity.

## 5. Third-party material

Third-party code, engine binaries, neural-network weights, fonts, quotations, screenshots, board assets, data, and other material remain under their original licenses or terms.

Their inclusion in this repository does not relicense them under AGPL or CC BY-SA.

Third-party material should be identified in `THIRD_PARTY_NOTICES.md` or alongside the relevant file.

## 6. Contributions

Unless a contribution is explicitly accepted under different written terms, contributions are provided under the license applicable to the part of the repository being changed:

- software contributions: AGPL-3.0-only;
- educational-content contributions: CC BY-SA 4.0.

Contributors retain copyright in their contributions while granting the permissions required by the applicable license.

## 7. No warranty

The software and educational material are provided without warranty, subject to the full terms of their applicable licenses.

This summary is provided for clarity and does not replace the legal license texts.
