# Read the accepted Sage vs GNU Stage 1 website snapshot.
#
# This file is intentionally limited to website-local loading. It does not
# calculate True ER, aggregate distributions, or implement reusable plots.

find_bms_repository_root <- function(start = getwd()) {
  current <- normalizePath(start, winslash = "/", mustWork = TRUE)

  repeat {
    marker <- file.path(current, "site", "_quarto.yml")
    if (file.exists(marker)) {
      return(current)
    }

    parent <- dirname(current)
    if (identical(parent, current)) {
      stop(
        "Could not find the repository root containing site/_quarto.yml.",
        call. = FALSE
      )
    }
    current <- parent
  }
}

stage1_release_root <- function(repo_root = find_bms_repository_root()) {
  file.path(
    repo_root,
    "site",
    "data",
    "engine-benchmark",
    "sage-vs-gnu-stage1",
    "v1"
  )
}

stage1_release_files <- function() {
  c(
    "README.md",
    "DATA_DICTIONARY.md",
    "VALIDATION_SUMMARY.md",
    "RELEASE_MANIFEST.json",
    "SOURCE_PROVENANCE.json",
    "inventory.tsv",
    "checksums.sha256",
    "core/match_level.csv",
    "core/match_results.csv",
    "core/performance_long.csv",
    "core/pair_results.csv",
    "core/pooled_true_er.csv",
    "core/runtime_match_level.csv",
    "core/runtime_summary.csv",
    "research/leave_one_pair_out.csv"
  )
}

stage1_table_files <- function() {
  c(
    match_level = "core/match_level.csv",
    match_results = "core/match_results.csv",
    performance_long = "core/performance_long.csv",
    pair_results = "core/pair_results.csv",
    pooled_true_er = "core/pooled_true_er.csv",
    runtime_match_level = "core/runtime_match_level.csv",
    runtime_summary = "core/runtime_summary.csv",
    leave_one_pair_out = "research/leave_one_pair_out.csv"
  )
}

read_stage1_csv <- function(path) {
  utils::read.csv(
    path,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    na.strings = c("", "NA")
  )
}

read_stage1_release <- function(
  release_root = stage1_release_root(),
  require_complete = FALSE
) {
  expected <- stage1_release_files()
  missing <- expected[!file.exists(file.path(release_root, expected))]

  if (length(missing) > 0L) {
    message_text <- paste0(
      "The accepted Stage 1 website snapshot is incomplete or not installed. ",
      "Missing: ",
      paste(missing, collapse = ", ")
    )

    if (isTRUE(require_complete)) {
      stop(message_text, call. = FALSE)
    }

    return(list(
      status = "pending",
      release_root = release_root,
      missing_files = missing,
      tables = list()
    ))
  }

  table_paths <- file.path(release_root, stage1_table_files())
  tables <- lapply(table_paths, read_stage1_csv)

  list(
    status = "available",
    release_root = release_root,
    missing_files = character(),
    tables = tables,
    documentation = list(
      readme = file.path(release_root, "README.md"),
      data_dictionary = file.path(release_root, "DATA_DICTIONARY.md"),
      validation_summary = file.path(release_root, "VALIDATION_SUMMARY.md"),
      release_manifest = file.path(release_root, "RELEASE_MANIFEST.json"),
      source_provenance = file.path(release_root, "SOURCE_PROVENANCE.json"),
      inventory = file.path(release_root, "inventory.tsv"),
      checksums = file.path(release_root, "checksums.sha256")
    )
  )
}
