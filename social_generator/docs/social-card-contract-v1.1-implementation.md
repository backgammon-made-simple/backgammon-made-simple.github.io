# Backgammon Made Simple Social Card Contract

**Contract version:** 1.1  
**Status:** Frozen for current implementation  
**Repository:** `backgammon-made-simple.github.io`

## Purpose

Defines the interface between website metadata, the R generator, the
Python/Chromium renderer, and Quarto publication.

The manifest is generated renderer input, not the editorial source of truth.

## Current implementation decisions

- The manifest contains exactly the frozen nine fields.
- The six frozen `kind` values select text-only layout profiles.
- Production cards accept only `visual: ""`.
- Source Sans 3 is loaded only from pinned local TrueType files.
- Every character used by the current manifest is checked against the local
  font cmap before Chromium starts rendering.
- HTTP and HTTPS requests are blocked.
- Output paths and the generated directory are resolved through symlinks and
  must remain inside the repository.
- Title and subtitle text may shrink only through predefined font-size ladders.
- Text is never rewritten, truncated, hidden, clipped, or ellipsized.
- PNGs are checked after capture for readability and exact dimensions.

This document records implementation alignment. The complete frozen contract is
owned by Left Brain and remains the acceptance source of truth.
