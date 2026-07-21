# Composition contract for the Sage vs GNU Stage 1 report.
#
# This file records the page-specific objects that later R handoffs may supply.
# It intentionally contains no reusable calculations or plotting functions.

stage1_page_slots <- function() {
  data.frame(
    slot = c(
      "pair_outcomes",
      "match_win_summary",
      "pooled_overall_true_er",
      "checker_cube_true_er",
      "pair_level_difference",
      "match_level_variation",
      "runtime"
    ),
    source = c(
      "core/pair_results.csv",
      "core/match_results.csv",
      "core/pooled_true_er.csv",
      "core/pooled_true_er.csv",
      "core/pair_results.csv or accepted derived output",
      "core/match_level.csv or core/performance_long.csv",
      "core/runtime_match_level.csv and core/runtime_summary.csv"
    ),
    current_state = "pending accepted R output",
    stringsAsFactors = FALSE
  )
}

compose_stage1_page <- function(
  figures = list(),
  tables = list(),
  interpretation = NULL
) {
  required_figures <- c(
    "pair_outcomes",
    "pooled_overall_true_er",
    "checker_cube_true_er",
    "pair_level_difference",
    "match_level_variation",
    "runtime"
  )

  required_tables <- "match_win_summary"

  list(
    figures = figures,
    tables = tables,
    interpretation = interpretation,
    missing_figures = setdiff(required_figures, names(figures)),
    missing_tables = setdiff(required_tables, names(tables)),
    ready = all(required_figures %in% names(figures)) &&
      all(required_tables %in% names(tables)) &&
      is.character(interpretation) &&
      length(interpretation) == 1L &&
      nzchar(interpretation)
  )
}

# Internal future integration point:
# A validated decision-level Sage error dataset should normally be published as
# a separate Research post. Add only a short report callout/link after that post
# and dataset are accepted. Never derive example errors from aggregate CSVs.
