# Validate the accepted Sage vs GNU Stage 1 website snapshot.
#
# Usage from the repository root:
#   Rscript scripts/engine-benchmark/sage-vs-gnu-stage1/validate_release.R
#
# The accepted release already owns the governed calculations. This script
# checks the website copy: required files, release checksums, expected row
# counts, and optionally exact analytical keys supplied after schema review.

script_path <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) == 0L) {
    return(NULL)
  }
  sub("^--file=", "", file_arg[[1]])
}

source_read_release <- function() {
  path <- script_path()
  if (is.null(path)) {
    source(file.path(
      "scripts", "engine-benchmark", "sage-vs-gnu-stage1", "read_release.R"
    ))
  } else {
    source(file.path(dirname(normalizePath(path)), "read_release.R"))
  }
}

source_read_release()

stage1_expected_rows <- function() {
  c(
    match_level = 40L,
    match_results = 20L,
    performance_long = 120L,
    pair_results = 10L,
    pooled_true_er = 6L,
    runtime_match_level = 20L,
    runtime_summary = 3L,
    leave_one_pair_out = 10L
  )
}

parse_sha256_manifest <- function(path) {
  lines <- trimws(readLines(path, warn = FALSE))
  lines <- lines[nzchar(lines) & !startsWith(lines, "#")]
  pattern <- "^([0-9A-Fa-f]{64})[[:space:]]+\\*?(.+)$"
  matched <- grepl(pattern, lines)

  if (!all(matched)) {
    stop(
      "Could not parse one or more lines in checksums.sha256.",
      call. = FALSE
    )
  }

  data.frame(
    expected_sha256 = tolower(sub(pattern, "\\1", lines)),
    relative_path = sub(pattern, "\\2", lines),
    stringsAsFactors = FALSE
  )
}

sha256_file <- function(path) {
  if (requireNamespace("digest", quietly = TRUE)) {
    return(tolower(digest::digest(
      path,
      algo = "sha256",
      file = TRUE,
      serialize = FALSE
    )))
  }

  if (requireNamespace("openssl", quietly = TRUE)) {
    return(tolower(as.character(openssl::sha256(file(path)))))
  }

  sha256sum <- Sys.which("sha256sum")
  if (nzchar(sha256sum)) {
    output <- system2(sha256sum, shQuote(path), stdout = TRUE, stderr = TRUE)
    if (length(output) == 0L) {
      stop("sha256sum returned no output.", call. = FALSE)
    }
    return(tolower(strsplit(trimws(output[[1]]), "[[:space:]]+")[[1]][1]))
  }

  certutil <- Sys.which("certutil")
  if (nzchar(certutil)) {
    output <- system2(
      certutil,
      c("-hashfile", shQuote(path), "SHA256"),
      stdout = TRUE,
      stderr = TRUE
    )
    candidate <- grep("^[0-9A-Fa-f ]{64,}$", trimws(output), value = TRUE)
    if (length(candidate) > 0L) {
      return(tolower(gsub("[[:space:]]", "", candidate[[1]])))
    }
  }

  stop(
    paste(
      "No SHA-256 implementation is available.",
      "Install the R package 'digest' or run from an environment with",
      "sha256sum or certutil."
    ),
    call. = FALSE
  )
}

validate_stage1_checksums <- function(release_root) {
  manifest <- parse_sha256_manifest(file.path(release_root, "checksums.sha256"))
  full_paths <- file.path(release_root, manifest$relative_path)
  manifest$file_exists <- file.exists(full_paths)
  manifest$actual_sha256 <- NA_character_

  existing <- which(manifest$file_exists)
  manifest$actual_sha256[existing] <- vapply(
    full_paths[existing],
    sha256_file,
    character(1)
  )

  manifest$matches <- manifest$file_exists &
    manifest$actual_sha256 == manifest$expected_sha256

  manifest
}

validate_stage1_rows <- function(tables) {
  expected <- stage1_expected_rows()
  actual <- vapply(tables[names(expected)], nrow, integer(1))

  data.frame(
    table = names(expected),
    expected_rows = unname(expected),
    actual_rows = unname(actual),
    matches = unname(expected) == unname(actual),
    stringsAsFactors = FALSE
  )
}

validate_unique_keys <- function(tables, key_spec = NULL) {
  if (is.null(key_spec)) {
    return(data.frame(
      table = names(tables),
      status = "not_configured",
      detail = paste(
        "Exact analytical key columns must be supplied after comparing",
        "the accepted CSV headers with DATA_DICTIONARY.md."
      ),
      stringsAsFactors = FALSE
    ))
  }

  results <- lapply(names(key_spec), function(table_name) {
    keys <- key_spec[[table_name]]
    table <- tables[[table_name]]

    if (is.null(table)) {
      return(data.frame(
        table = table_name,
        status = "missing_table",
        detail = "Table is not loaded.",
        stringsAsFactors = FALSE
      ))
    }

    missing_columns <- setdiff(keys, names(table))
    if (length(missing_columns) > 0L) {
      return(data.frame(
        table = table_name,
        status = "missing_key_columns",
        detail = paste(missing_columns, collapse = ", "),
        stringsAsFactors = FALSE
      ))
    }

    duplicated_key <- duplicated(table[keys])
    data.frame(
      table = table_name,
      status = if (any(duplicated_key)) "duplicate_keys" else "pass",
      detail = if (any(duplicated_key)) {
        paste(sum(duplicated_key), "duplicate key rows")
      } else {
        paste("Unique by", paste(keys, collapse = " + "))
      },
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, results)
}

validate_stage1_release <- function(
  release_root = stage1_release_root(),
  key_spec = NULL
) {
  release <- read_stage1_release(release_root, require_complete = TRUE)
  checksum_result <- validate_stage1_checksums(release_root)
  row_result <- validate_stage1_rows(release$tables)
  key_result <- validate_unique_keys(release$tables, key_spec = key_spec)

  list(
    release_root = release_root,
    checksums = checksum_result,
    rows = row_result,
    keys = key_result,
    checksum_pass = all(checksum_result$matches),
    row_count_pass = all(row_result$matches),
    key_status = if (is.null(key_spec)) "pending_schema_configuration" else {
      if (all(key_result$status == "pass")) "pass" else "fail"
    }
  )
}

print_stage1_validation <- function(result) {
  cat("Sage vs GNU Stage 1 website snapshot validation\n")
  cat("================================================\n\n")
  cat("Release root: ", result$release_root, "\n\n", sep = "")

  cat("Checksums\n")
  cat("---------\n")
  print(result$checksums[, c(
    "relative_path", "file_exists", "matches"
  )], row.names = FALSE)
  cat("Checksum status: ", if (result$checksum_pass) "PASS" else "FAIL", "\n\n", sep = "")

  cat("Row counts\n")
  cat("----------\n")
  print(result$rows, row.names = FALSE)
  cat("Row-count status: ", if (result$row_count_pass) "PASS" else "FAIL", "\n\n", sep = "")

  cat("Analytical keys\n")
  cat("---------------\n")
  print(result$keys, row.names = FALSE)
  cat("Key status: ", result$key_status, "\n", sep = "")
}

if (sys.nframe() == 0L && !interactive()) {
  result <- validate_stage1_release()
  print_stage1_validation(result)

  if (!result$checksum_pass || !result$row_count_pass || result$key_status == "fail") {
    quit(status = 1L)
  }
}
