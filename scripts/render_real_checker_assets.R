args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) {
  stop(
    paste(
      "Usage: render_real_checker_assets.R",
      "FIXTURE_DIR PROJECTION_JSON BACKGAMMONBOARD_REPO OUTPUT_DIR"
    ),
    call. = FALSE
  )
}

fixture_dir <- args[[1L]]
projection_path <- args[[2L]]
board_repo <- args[[3L]]
output_dir <- args[[4L]]

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("The jsonlite package is required.", call. = FALSE)
}
if (!requireNamespace("devtools", quietly = TRUE)) {
  stop("The devtools package is required.", call. = FALSE)
}
devtools::load_all(board_repo, quiet = TRUE)

read_object <- function(path) {
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

position_document <- read_object(file.path(fixture_dir, "position.json"))
analysis_document <- read_object(file.path(fixture_dir, "analysis.json"))
view_document <- read_object(file.path(fixture_dir, "analyzer-view.json"))
projection <- read_object(projection_path)
fixture_id <- view_document$position_id
lesson_fixture <- projection$checker_cases[[fixture_id]]

stopifnot(
  identical(position_document$position_id, view_document$position_id),
  identical(analysis_document$analysis_id, view_document$analysis_id),
  identical(lesson_fixture$position_id, view_document$position_id),
  identical(lesson_fixture$state_hash, view_document$state_hash),
  identical(lesson_fixture$analysis_id, view_document$analysis_id)
)

arrangement_to_position <- function(document) {
  arrangement <- document$state$checker_arrangement
  player <- as.integer(unlist(arrangement$player_points_1_to_24_and_bar))
  opponent <- as.integer(unlist(arrangement$opponent_points_1_to_24_and_bar))
  stopifnot(length(player) == 25L, length(opponent) == 25L)

  points <- integer(24L)
  for (point in seq_len(24L)) {
    opponent_count <- opponent[[25L - point]]
    if (player[[point]] > 0L && opponent_count > 0L) {
      stop("Both players occupy the same canonical point.", call. = FALSE)
    }
    points[[point]] <- player[[point]] - opponent_count
  }

  state <- document$state
  position <- backgammon_position(
    "XGID=-b----E-C---eE---c-e----B-:0:0:1:31:2:5:0:7:10"
  )
  position$points <- points
  position$bar <- c(white = player[[25L]], black = opponent[[25L]])
  position$off <- c(
    white = as.integer(arrangement$player_borne_off),
    black = as.integer(arrangement$opponent_borne_off)
  )
  position$on_roll <- "white"
  position$dice <- as.integer(unlist(state$dice))
  position$action_marker <- paste0(position$dice, collapse = "")
  position$dice_action <- position$action_marker
  position$cube_value <- as.integer(state$cube$value)
  position$cube_owner <- if (identical(state$cube$owner, "centered")) {
    "center"
  } else {
    state$cube$owner
  }
  position$score_white <- as.integer(state$score$player)
  position$score_black <- as.integer(state$score$opponent)
  position$score <- c(
    white = position$score_white,
    black = position$score_black
  )
  position$match_length <- as.integer(state$score$match_length)
  position$is_crawford <- isTRUE(state$crawford)
  position$jacoby <- isTRUE(state$rules$jacoby)
  position
}

position_to_arrangement <- function(position) {
  player <- integer(25L)
  opponent <- integer(25L)
  for (point in seq_len(24L)) {
    player[[point]] <- max(position$points[[point]], 0L)
    opponent[[25L - point]] <- max(-position$points[[point]], 0L)
  }
  player[[25L]] <- unname(position$bar[["white"]])
  opponent[[25L]] <- unname(position$bar[["black"]])
  list(
    player_borne_off = unname(position$off[["white"]]),
    player_points_1_to_24_and_bar = as.list(player),
    opponent_borne_off = unname(position$off[["black"]]),
    opponent_points_1_to_24_and_bar = as.list(opponent),
    perspective = "decision_player"
  )
}

arrangements_equal <- function(actual, expected) {
  identical(actual$perspective, expected$perspective) &&
    identical(as.integer(actual$player_borne_off), as.integer(expected$player_borne_off)) &&
    identical(as.integer(actual$opponent_borne_off), as.integer(expected$opponent_borne_off)) &&
    identical(
      as.integer(unlist(actual$player_points_1_to_24_and_bar)),
      as.integer(unlist(expected$player_points_1_to_24_and_bar))
    ) &&
    identical(
      as.integer(unlist(actual$opponent_points_1_to_24_and_bar)),
      as.integer(unlist(expected$opponent_points_1_to_24_and_bar))
    )
}

save_svg <- function(plot, path) {
  grDevices::svg(path, width = 10.625, height = 7.5, bg = "white")
  print(plot)
  grDevices::dev.off()
  stopifnot(file.exists(path), file.info(path)$size > 0)
}

position <- arrangement_to_position(position_document)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

starting <- ggboard(
  position,
  colors = board_colors("bms"),
  style = board_style("bms"),
  decision = "checker_play",
  perspective = "white",
  show_information = TRUE,
  brand_text = "Backgammon\nMade Simple"
)
save_svg(starting, file.path(output_dir, lesson_fixture$initial$image))

view_by_rank <- setNames(
  view_document$candidates,
  vapply(view_document$candidates, function(item) as.character(item$rank), character(1L))
)

for (candidate in lesson_fixture$candidates) {
  source <- view_by_rank[[as.character(candidate$rank)]]
  stopifnot(
    identical(candidate$move, source$move),
    identical(candidate$resulting_position_id, source$resulting_position_id)
  )
  plot <- ggboard(
    position,
    colors = board_colors("bms"),
    style = board_style("bms"),
    decision = "checker_play",
    perspective = "white",
    show_information = TRUE,
    brand_text = "Backgammon\nMade Simple",
    moves = candidate$move
  )
  actual <- position_to_arrangement(attr(plot, "backgammon_display_position"))
  if (!arrangements_equal(actual, source$resulting_position)) {
    stop(
      paste0(
        "Rendered result does not match analyzer-view for rank ",
        candidate$rank,
        ".\nActual: ",
        jsonlite::toJSON(actual, auto_unbox = TRUE),
        "\nExpected: ",
        jsonlite::toJSON(source$resulting_position, auto_unbox = TRUE)
      ),
      call. = FALSE
    )
  }
  save_svg(plot, file.path(output_dir, candidate$image))
}

message("PASS: rendered starting position and three verified checker candidates.")
