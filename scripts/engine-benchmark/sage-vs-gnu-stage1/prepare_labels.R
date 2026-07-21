# Page-specific public labels for the Sage vs GNU Stage 1 report.
#
# These helpers only change display labels. They do not filter observations,
# calculate True ER, pool values, or alter governed fields.

stage1_public_labels <- function() {
  list(
    experiment = "Sage vs GNU Stage 1",
    engines = c(
      sage = "Sage",
      gnubg = "GNU Backgammon",
      gnu = "GNU Backgammon"
    ),
    components = c(
      checker = "Checker play",
      cube = "Cube decisions",
      overall = "Overall"
    ),
    metric = "GNU-reviewed True ER",
    metric_scale = "500 scale",
    scope = "10 mirrored pairs · 20 seven-point matches",
    status = "Descriptive pilot"
  )
}

replace_public_labels <- function(x, labels) {
  output <- as.character(x)
  matched <- match(output, names(labels))
  replace <- !is.na(matched)
  output[replace] <- unname(labels[matched[replace]])
  output
}

prepare_stage1_labels <- function(
  data,
  engine_column = NULL,
  component_column = NULL
) {
  stopifnot(is.data.frame(data))
  output <- data
  labels <- stage1_public_labels()

  if (!is.null(engine_column)) {
    if (!engine_column %in% names(output)) {
      stop("Unknown engine column: ", engine_column, call. = FALSE)
    }
    output[[engine_column]] <- replace_public_labels(
      output[[engine_column]],
      labels$engines
    )
  }

  if (!is.null(component_column)) {
    if (!component_column %in% names(output)) {
      stop("Unknown component column: ", component_column, call. = FALSE)
    }
    output[[component_column]] <- replace_public_labels(
      output[[component_column]],
      labels$components
    )
  }

  output
}
