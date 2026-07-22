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
  file.path(dirname(script_path), "..", "..", ".."),
  winslash = "/",
  mustWork = TRUE
)

if (!requireNamespace("yaml", quietly = TRUE)) {
  stop("R package 'yaml' is required.", call. = FALSE)
}

site_root <- file.path(repo_root, "site")
manifest_path <- file.path(site_root, "assets", "social", "social-cards.yml")

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0) y else x
}

as_text <- function(value, field, path, allow_blank = FALSE) {
  if (!is.character(value) || length(value) != 1) {
    stop(sprintf("%s must have one text value in %s.", field, path), call. = FALSE)
  }
  value <- enc2utf8(value)
  if (!allow_blank && !nzchar(trimws(value))) {
    stop(sprintf("%s must not be blank in %s.", field, path), call. = FALSE)
  }
  value
}

read_front_matter <- function(path) {
  lines <- readLines(path, warn = FALSE, encoding = "UTF-8")
  if (length(lines) == 0 || trimws(sub("^\ufeff", "", lines[1])) != "---") {
    return(list())
  }
  closing <- which(trimws(lines[-1]) %in% c("---", "..."))
  if (length(closing) == 0) {
    stop(sprintf("Unclosed YAML front matter in %s.", path), call. = FALSE)
  }
  yaml_lines <- if (closing[1] == 1) character() else lines[2:closing[1]]
  yaml::yaml.load(paste(yaml_lines, collapse = "\n")) %||% list()
}

is_true <- function(value) {
  isTRUE(value) || (
    is.character(value) && length(value) == 1 &&
      tolower(trimws(value)) %in% c("true", "yes", "1")
  )
}

page_slug <- function(path, metadata) {
  explicit <- metadata[["social-card-slug"]] %||%
    metadata[["social_card_slug"]] %||%
    metadata[["social-slug"]] %||%
    metadata[["social_slug"]] %||%
    metadata[["slug"]]
  if (!is.null(explicit)) return(as_text(explicit, "social-card-slug", path))
  if (basename(path) == "index.qmd") return(basename(dirname(path)))
  tools::file_path_sans_ext(basename(path))
}

make_card <- function(slug, kind, title, subtitle, category = "") {
  github <- identical(kind, "github")
  output_name <- if (github || identical(slug, "social-default")) {
    paste0(slug, ".png")
  } else {
    paste0("social-", slug, ".png")
  }
  list(
    slug = slug,
    kind = kind,
    width = if (github) 1280L else 1200L,
    height = if (github) 640L else 630L,
    output = paste0("site/assets/social/generated/", output_name),
    title = title,
    subtitle = subtitle,
    category = category,
    visual = ""
  )
}

home_path <- file.path(site_root, "index.qmd")
home <- read_front_matter(home_path)

cards <- list(
  make_card(
    "social-default",
    "default",
    as_text(home$title, "title", home_path),
    as_text(home$description, "description", home_path)
  ),
  make_card(
    "github-backgammon-made-simple",
    "github",
    as_text(home$title, "title", home_path),
    "Question-driven lessons, position analysis and backgammon research."
  )
)

qmd_files <- list.files(site_root, pattern = "\\.qmd$", recursive = TRUE, full.names = TRUE)

for (path in qmd_files) {
  path <- normalizePath(path, winslash = "/", mustWork = TRUE)
  if (identical(path, normalizePath(home_path, winslash = "/", mustWork = TRUE))) next

  metadata <- read_front_matter(path)
  if (!is_true(metadata[["social-card"]] %||% metadata[["social_card"]])) next

  kind <- as_text(metadata[["social-card-kind"]] %||% metadata[["social_card_kind"]], "social-card-kind", path)
  category <- as_text(
    metadata[["social-card-category"]] %||% metadata[["social_card_category"]] %||% "",
    "social-card-category",
    path,
    allow_blank = TRUE
  )
  cards[[length(cards) + 1L]] <- make_card(
    page_slug(path, metadata),
    kind,
    as_text(metadata[["social-title"]] %||% metadata[["social_title"]] %||% metadata$title, "social-title", path),
    as_text(
      metadata[["social-subtitle"]] %||%
        metadata[["social_subtitle"]] %||%
        metadata[["social-card-subtitle"]] %||%
        metadata$description %||%
        "",
      "social-subtitle",
      path,
      allow_blank = TRUE
    ),
    category
  )
}

dir.create(dirname(manifest_path), recursive = TRUE, showWarnings = FALSE)
yaml::write_yaml(list(cards = cards), manifest_path, fileEncoding = "UTF-8")
cat(sprintf("Generated %s with %d card(s).\n", manifest_path, length(cards)))
