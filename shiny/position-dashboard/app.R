library(shiny)

repo_root <- normalizePath(file.path(getwd(), "../.."), mustWork = FALSE)
shared_css_files <- c(
  file.path(repo_root, "site", "assets", "bms-shared.css"),
  file.path(repo_root, "site", "assets", "bms-components.css"),
  file.path(repo_root, "shiny", "shared", "bms-shiny.css")
)
allowed_levels <- c("1ply", "2ply", "3ply", "4ply", "truncated1", "truncated2", "truncated3", "rollout")

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || all(is.na(x))) {
    return(y)
  }
  x
}

normalize_position_id <- function(position_id) {
  if (is.null(position_id) || length(position_id) == 0) {
    return(list(ok = FALSE, value = "", message = "Enter an XGID to preview the board."))
  }

  if (length(position_id) != 1) {
    return(list(ok = FALSE, value = "", message = "Enter exactly one position identifier."))
  }

  position_id <- as.character(position_id)
  if (is.na(position_id)) {
    return(list(ok = FALSE, value = "", message = "Enter an XGID to preview the board."))
  }

  if (grepl("[\r\n]", position_id)) {
    return(list(ok = FALSE, value = "", message = "Enter one XGID or GNUID on a single line."))
  }

  position_id <- trimws(position_id)
  if (!nzchar(position_id)) {
    return(list(ok = FALSE, value = "", message = "Enter an XGID to preview the board."))
  }

  list(ok = TRUE, value = position_id, message = "")
}

is_xgid <- function(position_id) {
  normalized <- normalize_position_id(position_id)
  isTRUE(normalized$ok) &&
    grepl("^XGID=[A-Za-z0-9+\\-]{26}(:-?[0-9]+){9}$", normalized$value)
}

board_state <- function(position_id) {
  normalized <- normalize_position_id(position_id)

  if (!isTRUE(normalized$ok)) {
    return(list(kind = "empty", message = normalized$message))
  }

  position_id <- normalized$value

  if (!is_xgid(position_id)) {
    return(list(
      kind = "unsupported",
      message = "Board preview currently requires one complete XGID. GNUID analysis can use the configured worker, but local preview is XGID-only."
    ))
  }

  missing_packages <- c("bglab", "ggplot2")[!vapply(c("bglab", "ggplot2"), requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing_packages) > 0) {
    return(list(
      kind = "missing-package",
      message = paste("Board rendering requires these R packages:", paste(missing_packages, collapse = ", "))
    ))
  }

  list(kind = "renderable", xgid = position_id, message = "Board preview")
}

render_bglab_board <- function(xgid) {
  withCallingHandlers(
    print(bglab::ggboard(xgid, scheme = "soft")),
    warning = function(warning) {
      message <- conditionMessage(warning)
      if (grepl("Using `size` aesthetic for lines was deprecated", message, fixed = TRUE)) {
        invokeRestart("muffleWarning")
      }
    }
  )
}

read_remote_text <- function(url) {
  con <- url(url, open = "rb")
  on.exit(close(con), add = TRUE)
  paste(readLines(con, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
}

worker_url <- function(base_url, position_id, level) {
  separator <- if (grepl("\\?", base_url, fixed = FALSE)) "&" else "?"
  paste0(
    base_url,
    separator,
    "xgid=", utils::URLencode(position_id, reserved = TRUE),
    "&ply=", utils::URLencode(level, reserved = TRUE)
  )
}

run_worker_analysis <- function(position_id, level) {
  base_url <- Sys.getenv("BMS_WORKER_BASE_URL", unset = "")
  if (!nzchar(base_url)) {
    return(list(
      schema_version = "worker-analysis-result-v0",
      analysis_id = NA,
      request_hash = NA,
      cache_status = "worker-not-configured",
      source = "worker-unconfigured",
      recommended_action = "Analysis worker is not configured in this environment.",
      warnings = character(),
      assumptions = c("set_BMS_WORKER_BASE_URL_for_analysis_results")
    ))
  }

  response_text <- tryCatch(
    read_remote_text(worker_url(base_url, position_id, level)),
    error = function(error) {
      return(list(error = conditionMessage(error)))
    }
  )

  if (is.list(response_text) && !is.null(response_text$error)) {
    return(list(
      schema_version = "worker-analysis-result-v0",
      analysis_id = NA,
      request_hash = NA,
      cache_status = "error",
      source = "remote-worker",
      recommended_action = "The configured analysis worker could not be reached.",
      warnings = c(response_text$error),
      assumptions = c("worker_request_failed")
    ))
  }

  output_url <- Sys.getenv("BMS_ANALYSIS_OUTPUT_URL", unset = "")
  result_text <- if (nzchar(output_url)) {
    tryCatch(
      read_remote_text(output_url),
      error = function(error) response_text
    )
  } else {
    response_text
  }

  parsed <- tryCatch(
    jsonlite::fromJSON(result_text, simplifyVector = FALSE),
    error = function(error) NULL
  )

  if (!is.null(parsed)) {
    return(parsed)
  }

  list(
    schema_version = "worker-analysis-result-v0",
    analysis_id = NA,
    request_hash = NA,
    cache_status = "remote",
    source = "remote-worker",
    recommended_action = "Remote worker response received",
    warnings = character(),
    assumptions = c("worker_text_output_not_yet_structured_json"),
    result_text = result_text
  )
}

run_analysis <- function(position_id, level) {
  if (!(level %in% allowed_levels)) {
    stop("Unsupported analysis level: ", level)
  }

  run_worker_analysis(position_id, level)
}

ui <- fluidPage(
  class = "bms-shiny-app",
  tags$head(
    lapply(shared_css_files[file.exists(shared_css_files)], includeCSS)
  ),
  div(
    class = "bms-page-shell",
    div(
      class = "bms-hero bms-shiny-hero",
      h1("Position Analyzer"),
      p("Preview an XGID board immediately, then request analysis when a server-side worker is configured.")
    ),
    div(
      class = "bms-analysis-shell",
      div(
        class = "bms-card bms-control-panel",
        h2("Analyze"),
        textInput(
          "position_id",
          "Position identifier",
          value = "",
          placeholder = "XGID=... or GNUID"
        ),
        selectInput(
          "level",
          "Sage level",
          choices = allowed_levels,
          selected = "1ply"
        ),
        actionButton("analyze", "Analyze Position", class = "bms-button-primary"),
        div(
          class = "bms-callout bms-compact-callout",
          div(class = "bms-callout-title", "Preview support"),
          "Local board preview is XGID-only. GNUID analysis is reserved for the configured worker path."
        )
      ),
      div(
        class = "bms-analysis-main",
        uiOutput("board_panel"),
        uiOutput("status_panel"),
        uiOutput("result_panel")
      )
    ),
    tags$footer(
      class = "bms-site-license",
      tags$p("© 2026 Marty Gale - Backgammon Made Simple"),
      tags$p("This lesson is available for non-commercial use under the PolyForm Noncommercial License 1.0.0. Reuse or adaptation must credit Backgammon Made Simple, identify Marty Gale as the original author, and reference the original page or repository. Commercial use requires written permission.")
    )
  )
)

server <- function(input, output, session) {
  result <- eventReactive(input$analyze, {
    normalized <- normalize_position_id(input$position_id)
    validate(need(isTRUE(normalized$ok), normalized$message))
    withProgress(message = "Analyzing position", value = 0.5, {
      run_analysis(normalized$value, input$level)
    })
  })

  current_board_state <- reactive({
    board_state(input$position_id)
  })

  output$board_panel <- renderUI({
    state <- current_board_state()
    if (identical(state$kind, "renderable")) {
      return(div(
        class = "bms-card",
        h2("Board Preview"),
        plotOutput("board_plot", height = "440px"),
        tags$p(class = "bms-identifier", state$xgid)
      ))
    }

    div(
      class = "bms-card",
      h2("Board Preview"),
      div(class = "bms-callout", div(class = "bms-callout-title", "Board unavailable"), state$message)
    )
  })

  output$board_plot <- renderPlot({
    state <- current_board_state()
    validate(need(identical(state$kind, "renderable"), state$message))
    tryCatch(
      {
        render_bglab_board(state$xgid)
      },
      error = function(error) {
        validate(need(
          FALSE,
          "Board preview could not render this XGID. Check that the identifier is complete and valid."
        ))
      }
    )
  }, res = 120)

  output$status_panel <- renderUI({
    if (input$analyze == 0) {
      div(
        class = "bms-card",
        h2("Analysis Queue"),
        tags$p(class = "bms-status bms-status--neutral", "Pending"),
        div(
          class = "bms-result-grid",
          div(
            class = "bms-result-slot",
            h3("Quick result"),
            p(class = "bms-muted", "Waiting for a worker-backed request.")
          ),
          div(
            class = "bms-result-slot",
            h3("Full result"),
            p(class = "bms-muted", "Streaming rows will appear here after the event contract is finalized.")
          )
        )
      )
    }
  })

  output$result_panel <- renderUI({
    data <- result()
    cache_status <- data$cache_status %||% "unknown"
    status_class <- if (identical(cache_status, "worker-not-configured")) {
      "bms-status bms-status--neutral"
    } else if (identical(cache_status, "error")) {
      "bms-status bms-status--mistake"
    } else {
      "bms-status bms-status--info"
    }

    tagList(
      div(
        class = "bms-card",
        h2("Result"),
        tags$p(class = status_class, cache_status),
        div(
          class = "bms-result-grid",
          div(
            class = "bms-result-slot",
            h3("Quick result"),
            p(class = "bms-muted", data$recommended_action %||% "No quick result returned.")
          ),
          div(
            class = "bms-result-slot",
            h3("Full result"),
            p(class = "bms-muted", "Detailed streamed rows are not wired until the worker event contract is final.")
          )
        ),
        tags$dl(
          tags$dt("Analysis ID"), tags$dd(data$analysis_id %||% "Not available"),
          tags$dt("Request hash"), tags$dd(data$request_hash %||% "Not available"),
          tags$dt("Cache status"), tags$dd(cache_status),
          tags$dt("Source"), tags$dd(data$source %||% "Not available"),
          tags$dt("Recommended action"), tags$dd(data$recommended_action %||% "No recommendation returned.")
        ),
        if (length(data$warnings) > 0) {
          tags$details(
            tags$summary("Warnings and assumptions"),
            tags$ul(lapply(c(data$warnings, data$assumptions), tags$li))
          )
        },
        if (!is.null(data$result_text)) {
          tags$details(
            open = TRUE,
            tags$summary("Worker output"),
            tags$pre(data$result_text)
          )
        },
        tags$details(
          tags$summary("Raw JSON"),
          tags$pre(jsonlite::toJSON(data, auto_unbox = TRUE, pretty = TRUE))
        )
      ),
      br()
    )
  })
}

shinyApp(ui, server)
