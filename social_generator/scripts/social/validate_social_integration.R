#!/usr/bin/env Rscript

args_full <- commandArgs(trailingOnly = FALSE)
script_arg <- grep("^--file=", args_full, value = TRUE)

if (length(script_arg) != 1) {
  stop("Could not determine this script's location.", call. = FALSE)
}

script_path <- normalizePath(
  sub("^--file=", "", script_arg),
  winslash = "/",
  mustWork = TRUE
)

repo_root <- normalizePath(
  file.path(dirname(script_path), "..", ".."),
  winslash = "/",
  mustWork = TRUE
)

if (!requireNamespace("yaml", quietly = TRUE)) {
  stop(
    "R package 'yaml' is required. Run install.packages('yaml').",
    call. = FALSE
  )
}

manifest_path <- file.path(
  repo_root,
  "site",
  "assets",
  "social",
  "social-cards.yml"
)

site_root <- file.path(repo_root, "site")
quarto_path <- file.path(repo_root, "_quarto.yml")

failures <- character()
add_failure <- function(message) {
  failures <<- c(failures, message)
}

`%+%` <- function(x, y) paste0(x, y)

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0) y else x
}

as_scalar_character <- function(value) {
  if (is.null(value) || length(value) == 0) return(NULL)
  if (is.character(value) && length(value) == 1) return(value)
  NULL
}

normalise_public_path <- function(path) {
  if (is.null(path)) return(NULL)
  path <- gsub("\\\\", "/", path)
  if (!startsWith(path, "/")) path <- paste0("/", path)
  path
}

read_front_matter <- function(path) {
  lines <- readLines(path, warn = FALSE, encoding = "UTF-8")

  if (length(lines) == 0) return(list())

  lines[1] <- sub("^\ufeff", "", lines[1])

  if (trimws(lines[1]) != "---") return(list())

  closing <- which(trimws(lines[-1]) %in% c("---", "..."))

  if (length(closing) == 0) {
    add_failure(
      sprintf(
        "%s has an opening YAML delimiter but no closing delimiter.",
        substring(path, nchar(repo_root) + 2)
      )
    )
    return(list())
  }

  closing_line <- closing[1] + 1
  yaml_lines <- if (closing_line <= 2) character() else lines[2:(closing_line - 1)]
  yaml_text <- paste(yaml_lines, collapse = "\n")

  tryCatch(
    yaml::yaml.load(yaml_text) %||% list(),
    error = function(error) {
      add_failure(
        sprintf(
          "Could not parse front matter in %s: %s",
          substring(path, nchar(repo_root) + 2),
          conditionMessage(error)
        )
      )
      list()
    }
  )
}

is_true <- function(value) {
  isTRUE(value) ||
    (is.character(value) &&
       length(value) == 1 &&
       tolower(trimws(value)) %in% c("true", "yes", "1"))
}

is_false <- function(value) {
  identical(value, FALSE) ||
    (is.character(value) &&
       length(value) == 1 &&
       tolower(trimws(value)) %in% c("false", "no", "0"))
}

metadata_value <- function(metadata, keys) {
  for (key in keys) {
    value <- metadata[[key]]
    if (!is.null(value)) return(value)
  }
  NULL
}

page_is_eligible <- function(metadata) {
  if (is_false(metadata_value(metadata, c("social-card", "social_card")))) {
    return(FALSE)
  }

  if (is_true(metadata[["draft"]])) return(FALSE)

  status <- as_scalar_character(metadata[["status"]])
  if (
    !is.null(status) &&
    tolower(trimws(status)) %in%
      c("planned", "draft", "private", "archived", "unpublished")
  ) {
    return(FALSE)
  }

  TRUE
}

infer_page_slug <- function(path, metadata) {
  explicit <- as_scalar_character(
    metadata_value(
      metadata,
      c(
        "social-card-slug",
        "social_card_slug",
        "social-slug",
        "social_slug",
        "slug"
      )
    )
  )

  if (!is.null(explicit) && nzchar(trimws(explicit))) {
    return(trimws(explicit))
  }

  relative <- substring(path, nchar(site_root) + 2)

  if (relative == "index.qmd") return("social-default")

  filename <- basename(path)

  if (filename == "index.qmd") {
    return(basename(dirname(path)))
  }

  tools::file_path_sans_ext(filename)
}

extract_page_image <- function(metadata) {
  image <- metadata[["image"]]

  if (is.character(image) && length(image) == 1) {
    return(image)
  }

  if (is.list(image)) {
    for (key in c("src", "path", "url")) {
      value <- as_scalar_character(image[[key]])
      if (!is.null(value)) return(value)
    }
  }

  open_graph <- metadata[["open-graph"]]
  if (is.list(open_graph)) {
    value <- as_scalar_character(open_graph[["image"]])
    if (!is.null(value)) return(value)
  }

  NULL
}

expected_public_image <- function(output) {
  normalise_public_path(sub("^site", "", output))
}

if (!file.exists(manifest_path)) {
  stop(sprintf("Missing manifest: %s", manifest_path), call. = FALSE)
}

manifest <- yaml::read_yaml(manifest_path)
cards <- manifest[["cards"]]

if (!is.list(cards)) {
  stop("Manifest cards must be a list.", call. = FALSE)
}

card_slugs <- vapply(cards, function(card) card[["slug"]], character(1))
card_kinds <- vapply(cards, function(card) card[["kind"]], character(1))
card_outputs <- vapply(cards, function(card) card[["output"]], character(1))

card_by_slug <- setNames(cards, card_slugs)

qmd_files <- list.files(
  site_root,
  pattern = "\\.qmd$",
  recursive = TRUE,
  full.names = TRUE
)

qmd_files <- normalizePath(
  qmd_files,
  winslash = "/",
  mustWork = TRUE
)

eligible_pages <- list()
seen_page_slugs <- character()

for (path in qmd_files) {
  metadata <- read_front_matter(path)

  if (!page_is_eligible(metadata)) next

  slug <- infer_page_slug(path, metadata)
  relative_path <- substring(path, nchar(repo_root) + 2)

  if (!grepl("^[a-z0-9]+(?:-[a-z0-9]+)*$", slug, perl = TRUE)) {
    add_failure(
      sprintf(
        "%s resolves to invalid social-card slug '%s'.",
        relative_path,
        slug
      )
    )
    next
  }

  if (slug %in% seen_page_slugs) {
    add_failure(
      sprintf("Multiple eligible QMD pages resolve to slug '%s'.", slug)
    )
    next
  }

  seen_page_slugs <- c(seen_page_slugs, slug)

  if (is.null(card_by_slug[[slug]])) {
    add_failure(
      sprintf(
        "Eligible page %s has no card record for slug '%s'.",
        relative_path,
        slug
      )
    )
    next
  }

  card <- card_by_slug[[slug]]

  if (identical(card[["kind"]], "github")) {
    add_failure(
      sprintf(
        "Eligible page %s maps to GitHub-only card '%s'.",
        relative_path,
        slug
      )
    )
    next
  }

  page_image <- extract_page_image(metadata)
  expected_image <- expected_public_image(card[["output"]])

  if (slug == "social-default") {
    if (!is.null(page_image)) {
      actual_image <- normalise_public_path(page_image)
      if (!identical(actual_image, expected_image)) {
        add_failure(
          sprintf(
            "Homepage image metadata is '%s'; expected '%s'.",
            actual_image,
            expected_image
          )
        )
      }
    }
  } else {
    if (is.null(page_image)) {
      add_failure(
        sprintf(
          "Eligible page %s is missing image metadata; expected '%s'.",
          relative_path,
          expected_image
        )
      )
    } else {
      actual_image <- normalise_public_path(page_image)
      if (!identical(actual_image, expected_image)) {
        add_failure(
          sprintf(
            "Page %s uses image '%s'; expected '%s'.",
            relative_path,
            actual_image,
            expected_image
          )
        )
      }
    }
  }

  eligible_pages[[slug]] <- relative_path
}

page_card_indices <- which(
  card_kinds != "github" &
    card_slugs != "social-default"
)

for (index in page_card_indices) {
  slug <- card_slugs[index]

  if (is.null(eligible_pages[[slug]])) {
    add_failure(
      sprintf(
        "Page card '%s' has no eligible QMD page. "
          %+% "Delete it, publish the page, or mark the correct page metadata.",
        slug
      )
    )
  }
}

if (!file.exists(quarto_path)) {
  add_failure("Missing _quarto.yml; cannot validate site fallback image.")
} else {
  quarto <- tryCatch(
    yaml::read_yaml(quarto_path),
    error = function(error) {
      add_failure(
        sprintf("Could not parse _quarto.yml: %s", conditionMessage(error))
      )
      list()
    }
  )

  fallback_card <- card_by_slug[["social-default"]]

  if (is.null(fallback_card)) {
    add_failure("Manifest is missing the social-default fallback card.")
  } else {
    expected_fallback <- expected_public_image(fallback_card[["output"]])
    website <- quarto[["website"]]
    actual_fallback <- NULL

    if (is.list(website)) {
      actual_fallback <- as_scalar_character(website[["image"]])

      if (is.null(actual_fallback) && is.list(website[["open-graph"]])) {
        actual_fallback <- as_scalar_character(
          website[["open-graph"]][["image"]]
        )
      }
    }

    if (is.null(actual_fallback)) {
      add_failure(
        sprintf(
          "_quarto.yml is missing website.image; expected '%s'.",
          expected_fallback
        )
      )
    } else if (
      !identical(
        normalise_public_path(actual_fallback),
        expected_fallback
      )
    ) {
      add_failure(
        sprintf(
          "_quarto.yml website.image is '%s'; expected '%s'.",
          normalise_public_path(actual_fallback),
          expected_fallback
        )
      )
    }
  }
}

if (length(failures) > 0) {
  cat("Social-card repository integration validation failed:\n", sep = "")
  for (failure in failures) {
    cat("- ", failure, "\n", sep = "")
  }
  quit(status = 1)
}

cat(
  sprintf(
    "Social-card repository integration validation passed: "
      %+% "%d eligible pages, %d manifest cards.\n",
    length(eligible_pages),
    length(cards)
  )
)
