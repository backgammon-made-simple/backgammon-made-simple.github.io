library(shiny)

# Public position-preview prototype:
# accept an XGID, normalize it, and render the position with bglab::ggboard().

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0L || all(is.na(x))) {
    return(y)
  }
  x
}

invalid_xgid_message <- "Check that the identifier was copied in full."

normalize_xgid <- function(value) {
  if (is.null(value) || length(value) == 0L) {
    return(list(ok = FALSE, value = "", message = invalid_xgid_message))
  }
  
  if (length(value) != 1L) {
    return(list(ok = FALSE, value = "", message = invalid_xgid_message))
  }
  
  value <- as.character(value)
  
  if (is.na(value) || grepl("[\r\n]", value)) {
    return(list(ok = FALSE, value = "", message = invalid_xgid_message))
  }
  
  value <- trimws(value)
  
  if (!nzchar(value)) {
    return(list(ok = FALSE, value = "", message = invalid_xgid_message))
  }
  
  complete_pattern <- "^XGID=[A-Za-z0-9+\\-]{26}(:-?[0-9]+){9}$"
  bare_pattern <- "^[A-Za-z0-9+\\-]{26}(:-?[0-9]+){9}$"
  
  if (grepl(complete_pattern, value)) {
    return(list(ok = TRUE, value = value, message = ""))
  }
  
  if (grepl(bare_pattern, value)) {
    return(list(ok = TRUE, value = paste0("XGID=", value), message = ""))
  }
  
  list(
    ok = FALSE,
    value = value,
    message = invalid_xgid_message
  )
}

render_bglab_board <- function(xgid) {
  withCallingHandlers(
    print(bglab::ggboard(xgid, scheme = "soft")),
    warning = function(warning) {
      warning_message <- conditionMessage(warning)
      if (grepl("Using `size` aesthetic for lines was deprecated", warning_message, fixed = TRUE)) {
        invokeRestart("muffleWarning")
      }
    }
  )
}

css_path <- file.path(getwd(), "www", "bms-shiny.css")

iframe_resize_script <- HTML(
  "
(function () {
  const messageType = 'bms-iframe-height';
  const requestType = 'bms-request-height';
  const sourceName = 'position-dashboard';

  let lastHeight = 0;
  let scheduledFrame = null;

  if (window.self !== window.top) {
    document.documentElement.classList.add('bms-embedded');
  }

  function measureHeight() {
    scheduledFrame = null;

    const body = document.body;
    const content = document.querySelector('.bms-preview-shell');

    const height = content
      ? Math.ceil(content.getBoundingClientRect().bottom + window.scrollY)
      : Math.ceil(body ? body.scrollHeight : 0);

    if (!Number.isFinite(height) || height < 1) {
      return;
    }

    if (Math.abs(height - lastHeight) < 2) {
      return;
    }

    lastHeight = height;

    window.parent.postMessage(
      {
        type: messageType,
        source: sourceName,
        height: height
      },
      '*'
    );
  }

  function scheduleHeightReport() {
    if (scheduledFrame !== null) {
      window.cancelAnimationFrame(scheduledFrame);
    }

    scheduledFrame = window.requestAnimationFrame(measureHeight);
  }

  window.addEventListener('load', scheduleHeightReport);
  window.addEventListener('resize', scheduleHeightReport);

  window.addEventListener('message', function (event) {
    if (event.data && event.data.type === requestType) {
      scheduleHeightReport();
    }
  });

  document.addEventListener('shiny:connected', scheduleHeightReport);
  document.addEventListener('shiny:value', scheduleHeightReport);
  document.addEventListener('shiny:idle', scheduleHeightReport);

  if ('ResizeObserver' in window) {
    const resizeObserver = new ResizeObserver(scheduleHeightReport);
    resizeObserver.observe(document.documentElement);

    if (document.body) {
      resizeObserver.observe(document.body);
    }
  }

  if ('MutationObserver' in window && document.body) {
    const mutationObserver = new MutationObserver(scheduleHeightReport);
    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      characterData: true
    });
  }

  scheduleHeightReport();
})();
  "
)

ui <- fluidPage(
  class = "bms-position-preview-app",
  tags$head(
    tags$meta(name = "viewport", content = "width=device-width, initial-scale=1"),
    if (file.exists(css_path)) includeCSS(css_path),
    tags$script(iframe_resize_script)
  ),
  div(
    class = "bms-preview-shell",
    div(
      class = "bms-preview-controls",
      div(
        class = "bms-preview-input",
        textInput(
          inputId = "position_id",
          label = "Enter XGID:",
          value = "",
          placeholder = "XGID=..."
        )
      ),
      actionButton(
        inputId = "show_position",
        label = "Show Position",
        class = "bms-preview-button"
      )
    ),
    uiOutput("message_panel"),
    uiOutput("board_panel")
  )
)

server <- function(input, output, session) {
  submitted_xgid <- reactiveVal("")
  
  observeEvent(
    session$clientData$url_search,
    {
      query_string <- session$clientData$url_search %||% ""
      query <- shiny::parseQueryString(query_string)
      position <- query[["position"]]
      
      if (
        !is.null(position) &&
        length(position) == 1L &&
        !is.na(position) &&
        nzchar(trimws(position))
      ) {
        normalized <- normalize_xgid(position)
        display_value <- if (isTRUE(normalized$ok)) normalized$value else trimws(position)
        
        updateTextInput(
          session = session,
          inputId = "position_id",
          value = display_value
        )
        
        submitted_xgid(display_value)
      }
    },
    ignoreInit = FALSE,
    once = TRUE
  )
  
  observeEvent(input$show_position, {
    submitted_xgid(input$position_id)
  }, ignoreInit = TRUE)
  
  current_state <- reactive({
    normalize_xgid(submitted_xgid())
  })
  
  output$message_panel <- renderUI({
    if (!nzchar(submitted_xgid())) {
      return(NULL)
    }
    
    state <- current_state()
    
    if (!isTRUE(state$ok)) {
      return(div(
        class = "bms-preview-message bms-preview-message--error",
        state$message
      ))
    }
    
    NULL
  })
  
  output$board_panel <- renderUI({
    state <- current_state()
    
    if (!isTRUE(state$ok)) {
      return(NULL)
    }
    
    missing_packages <- c("bglab", "ggplot2")[
      !vapply(c("bglab", "ggplot2"), requireNamespace, logical(1), quietly = TRUE)
    ]
    
    if (length(missing_packages) > 0L) {
      return(div(
        class = "bms-preview-message bms-preview-message--error",
        "Board rendering requires: ",
        paste(missing_packages, collapse = ", ")
      ))
    }
    
    div(
      class = "bms-board-card",
      tags$h2("Board Preview"),
      plotOutput("board_plot", height = "560px")
    )
  })
  
  output$board_plot <- renderPlot({
    state <- current_state()
    validate(need(isTRUE(state$ok), state$message))
    
    tryCatch(
      render_bglab_board(state$value),
      error = function(error) {
        validate(need(
          FALSE,
          "The board could not be rendered. Check that the XGID is complete and valid."
        ))
      }
    )
  }, res = 120)
}

shinyApp(ui, server)
