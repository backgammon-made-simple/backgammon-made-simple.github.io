(function () {
  "use strict";

  const MANIFEST_ROUTE = "/assets/bms-learn-sequence.json";
  const ID_TOKEN_ATTRIBUTES = [
    "for",
    "aria-activedescendant",
    "aria-controls",
    "aria-describedby",
    "aria-details",
    "aria-errormessage",
    "aria-flowto",
    "aria-labelledby",
    "aria-owns",
    "data-answer-panel",
    "data-anchor-id",
    "form",
    "headers",
    "list"
  ];
  const ID_HASH_ATTRIBUTES = [
    "data-bs-target",
    "data-target",
    "data-scroll-target"
  ];
  const URL_ATTRIBUTES = ["href", "src", "poster", "data-src"];

  function normalizeRoute(pathname) {
    let route = String(pathname || "").trim();
    try {
      if (/^[a-z][a-z0-9+.-]*:\/\//i.test(route)) {
        route = new URL(route).pathname;
      }
      route = decodeURI(route);
    } catch (_error) {
      // Retain the supplied route when it cannot be decoded.
    }
    route = route.split(/[?#]/, 1)[0].replace(/\\/g, "/");
    route = (route.startsWith("/") ? route : "/" + route).replace(/\/{2,}/g, "/");
    route = route.replace(/\/index\.html$/i, "/");
    route = route.replace(/\.html\/+$/i, ".html");
    if (
      route.length > 1 &&
      !route.endsWith("/") &&
      !/\/[^/]+\.[a-z0-9]+$/i.test(route)
    ) {
      route += "/";
    }
    return route || "/";
  }

  function lessonsFromManifest(manifest) {
    if (
      !manifest ||
      manifest.schema_version !== 1 ||
      !Array.isArray(manifest.lessons)
    ) {
      return [];
    }
    return manifest.lessons;
  }

  function findCurrentLesson(manifest, pathname) {
    const route = normalizeRoute(pathname);
    return (
      lessonsFromManifest(manifest).find(function (lesson) {
        return normalizeRoute(lesson.route) === route;
      }) || null
    );
  }

  function nextLesson(manifest, lesson) {
    if (!lesson || !lesson.next_route) {
      return null;
    }
    const lessons = lessonsFromManifest(manifest);
    const candidate = findCurrentLesson(manifest, lesson.next_route);
    if (
      !candidate ||
      candidate.sequence_index !== lesson.sequence_index + 1 ||
      normalizeRoute(candidate.previous_route) !== normalizeRoute(lesson.route)
    ) {
      return null;
    }
    return lessons[candidate.sequence_index] === candidate ? candidate : null;
  }

  function isFinalLesson(manifest, lesson) {
    return Boolean(lesson && !nextLesson(manifest, lesson));
  }

  function laterLessonRoutes(manifest, pathname) {
    const lesson = findCurrentLesson(manifest, pathname);
    if (!lesson) {
      return [];
    }
    return lessonsFromManifest(manifest)
      .slice(lesson.sequence_index + 1)
      .map(function (candidate) {
        return normalizeRoute(candidate.route);
      });
  }

  function idPrefixForRoute(route) {
    const parts = normalizeRoute(route).split("/").filter(Boolean);
    const filename = parts.pop() || "lesson";
    const slug = filename
      .replace(/\.html$/i, "")
      .toLocaleLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
    return "bms-learn-scroll-" + (slug || "lesson") + "-";
  }

  function rewriteIdReferences(root, prefix) {
    const idMap = new Map();
    root.querySelectorAll("[id]").forEach(function (element) {
      const oldId = element.id;
      const newId = prefix + oldId;
      idMap.set(oldId, newId);
      element.id = newId;
    });

    root.querySelectorAll("*").forEach(function (element) {
      ID_TOKEN_ATTRIBUTES.forEach(function (attribute) {
        const value = element.getAttribute(attribute);
        if (!value) {
          return;
        }
        element.setAttribute(
          attribute,
          value
            .split(/\s+/)
            .map(function (id) {
              return idMap.get(id) || id;
            })
            .join(" ")
        );
      });

      ["href", "xlink:href"].forEach(function (attribute) {
        const href = element.getAttribute(attribute);
        if (href && href.startsWith("#") && href.length > 1) {
          const target = href.slice(1);
          if (idMap.has(target)) {
            element.setAttribute(attribute, "#" + idMap.get(target));
          }
        }
      });

      ID_HASH_ATTRIBUTES.forEach(function (attribute) {
        const target = element.getAttribute(attribute);
        if (target && target.startsWith("#") && idMap.has(target.slice(1))) {
          element.setAttribute(attribute, "#" + idMap.get(target.slice(1)));
        }
      });

      Array.from(element.attributes || []).forEach(function (attribute) {
        const rewritten = attribute.value.replace(
          /url\(\s*#([^)\s]+)\s*\)/g,
          function (match, id) {
            return idMap.has(id) ? "url(#" + idMap.get(id) + ")" : match;
          }
        );
        if (rewritten !== attribute.value) {
          element.setAttribute(attribute.name, rewritten);
        }
      });
    });
    return idMap;
  }

  function isSafeDataUrl(value) {
    return /^data:(?:image|audio|video|font)\/[a-z0-9.+-]+[;,]/i.test(value);
  }

  function resolveUrlValue(value, baseUrl) {
    const original = String(value || "").trim();
    if (!original) {
      return original;
    }
    if (/^javascript:/i.test(original)) {
      return null;
    }
    if (original.startsWith("#") || /^(?:mailto|tel):/i.test(original)) {
      return original;
    }
    if (/^data:/i.test(original)) {
      return isSafeDataUrl(original) ? original : null;
    }
    if (/^(?:https?:)?\/\//i.test(original)) {
      return original;
    }
    if (original.startsWith("/")) {
      return original;
    }
    try {
      return new URL(original, baseUrl).href;
    } catch (_error) {
      return null;
    }
  }

  function resolveSrcset(value, baseUrl) {
    const original = String(value || "").trim();
    if (!original || /^data:/i.test(original)) {
      return !original || isSafeDataUrl(original) ? original : "";
    }
    const candidates = original.split(",").map(function (candidate) {
      const match = candidate.trim().match(/^(\S+)(\s+.*)?$/);
      if (!match) {
        return "";
      }
      const resolved = resolveUrlValue(match[1], baseUrl);
      return resolved === null ? "" : resolved + (match[2] || "");
    });
    return candidates.filter(Boolean).join(", ");
  }

  function rewriteResourceUrls(root, baseUrl) {
    root.querySelectorAll("*").forEach(function (element) {
      Array.from(element.attributes || []).forEach(function (attribute) {
        if (/^on/i.test(attribute.name)) {
          element.removeAttribute(attribute.name);
        }
      });
      URL_ATTRIBUTES.forEach(function (attribute) {
        if (!element.hasAttribute(attribute)) {
          return;
        }
        const resolved = resolveUrlValue(element.getAttribute(attribute), baseUrl);
        if (resolved === null) {
          element.removeAttribute(attribute);
        } else {
          element.setAttribute(attribute, resolved);
        }
      });
      if (element.hasAttribute("srcset")) {
        element.setAttribute(
          "srcset",
          resolveSrcset(element.getAttribute("srcset"), baseUrl)
        );
      }
    });
  }

  function sameOriginUrl(route, origin) {
    try {
      const url = new URL(route, origin);
      return url.origin === origin ? url : null;
    } catch (_error) {
      return null;
    }
  }

  function createLoadedRouteTracker(initialRoute) {
    const loaded = new Set([normalizeRoute(initialRoute)]);
    const inFlight = new Set();
    return {
      canFetch: function (route) {
        const normalized = normalizeRoute(route);
        return (
          inFlight.size === 0 &&
          !loaded.has(normalized) &&
          !inFlight.has(normalized)
        );
      },
      start: function (route) {
        const normalized = normalizeRoute(route);
        if (!this.canFetch(normalized)) {
          return false;
        }
        inFlight.add(normalized);
        return true;
      },
      complete: function (route) {
        const normalized = normalizeRoute(route);
        inFlight.delete(normalized);
        loaded.add(normalized);
      },
      fail: function (route) {
        inFlight.delete(normalizeRoute(route));
      },
      isLoaded: function (route) {
        return loaded.has(normalizeRoute(route));
      },
      isInFlight: function (route) {
        return inFlight.has(normalizeRoute(route));
      }
    };
  }

  function startsNewTrack(lesson) {
    return Boolean(lesson && lesson.next_starts_new_track);
  }

  function errorStateForLesson(lesson) {
    return {
      message: "The next lesson could not be loaded.",
      route: lesson ? normalizeRoute(lesson.route) : ""
    };
  }

  function createDivider(lesson, fetchedTitle, trackBoundary) {
    const divider = document.createElement("section");
    const label = document.createElement("span");
    const title = document.createElement("strong");
    const track = document.createElement("span");
    const visibleTitle = fetchedTitle || lesson.title;

    divider.className = "bms-learn-scroll-divider";
    if (trackBoundary) {
      divider.classList.add("is-track-boundary");
    }
    divider.dataset.bmsLearnScrollDivider = lesson.route;
    divider.setAttribute("aria-label", "Next lesson: " + visibleTitle);
    label.className = "bms-learn-scroll-divider-label";
    label.textContent = trackBoundary ? "Next track" : "Next lesson";
    title.className = "bms-learn-scroll-divider-title";
    title.textContent = visibleTitle;
    track.className = "bms-learn-scroll-divider-track";
    track.textContent = lesson.track_title;
    divider.append(label, title, track);
    return divider;
  }

  function createEndState() {
    const end = document.createElement("section");
    const message = document.createElement("p");
    const link = document.createElement("a");
    end.className = "bms-learn-scroll-end";
    end.dataset.bmsLearnScrollEnd = "";
    message.textContent = "You have reached the end of the current lessons.";
    link.href = "/learn/";
    link.textContent = "Return to Learn Home";
    end.append(message, link);
    return end;
  }

  function createErrorState(lesson, retry) {
    const state = errorStateForLesson(lesson);
    const container = document.createElement("div");
    const message = document.createElement("p");
    const link = document.createElement("a");
    const button = document.createElement("button");

    container.className = "bms-learn-scroll-error";
    container.setAttribute("role", "status");
    container.setAttribute("aria-live", "polite");
    message.textContent = state.message + " ";
    link.href = state.route;
    link.textContent = "Open it as a normal page.";
    button.type = "button";
    button.className = "bms-button-outline bms-learn-scroll-retry";
    button.textContent = "Retry";
    button.addEventListener("click", retry, { once: true });
    message.appendChild(link);
    container.append(message, button);
    return container;
  }

  function initializeContinuousLearn() {
    if (
      !("IntersectionObserver" in window) ||
      !document.getElementById("quarto-document-content")
    ) {
      return;
    }

    fetch(MANIFEST_ROUTE, { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Learn sequence failed to load");
        }
        return response.json();
      })
      .then(function (manifest) {
        const main = document.getElementById("quarto-document-content");
        const current = findCurrentLesson(manifest, window.location.pathname);
        if (!main || !current) {
          return;
        }

        const tracker = createLoadedRouteTracker(current.route);
        let observer = null;

        function showEndState() {
          if (!main.querySelector("[data-bms-learn-scroll-end]")) {
            main.appendChild(createEndState());
          }
        }

        function addSentinel(currentLesson) {
          const followingLesson = nextLesson(manifest, currentLesson);
          if (!followingLesson) {
            showEndState();
            return;
          }

          const sentinel = document.createElement("div");
          sentinel.className = "bms-learn-scroll-sentinel";
          sentinel.dataset.bmsLearnScrollSentinel = followingLesson.route;
          sentinel.setAttribute("aria-live", "polite");
          main.appendChild(sentinel);

          function attemptLoad() {
            const requestUrl = sameOriginUrl(
              followingLesson.route,
              window.location.origin
            );
            if (
              !requestUrl ||
              !findCurrentLesson(manifest, requestUrl.pathname) ||
              !tracker.start(followingLesson.route)
            ) {
              return;
            }

            if (observer) {
              observer.disconnect();
              observer = null;
            }
            sentinel.classList.add("is-loading");
            sentinel.textContent = "Loading the next lesson\u2026";

            fetch(requestUrl.href, { credentials: "same-origin" })
              .then(function (response) {
                if (!response.ok) {
                  throw new Error("Next lesson failed to load");
                }
                const finalUrl = sameOriginUrl(response.url, window.location.origin);
                if (
                  !finalUrl ||
                  normalizeRoute(finalUrl.pathname) !==
                    normalizeRoute(followingLesson.route)
                ) {
                  throw new Error("Next lesson redirected unexpectedly");
                }
                return response.text().then(function (html) {
                  return { html: html, finalUrl: finalUrl };
                });
              })
              .then(function (result) {
                const nextDocument = new DOMParser().parseFromString(
                  result.html,
                  "text/html"
                );
                const nextMain = nextDocument.getElementById(
                  "quarto-document-content"
                );
                if (
                  !nextMain ||
                  !nextDocument.body ||
                  !nextDocument.body.classList.contains("bms-learn-article")
                ) {
                  throw new Error("Next lesson content was not found");
                }

                const heading = nextMain.querySelector("h1");
                const fetchedTitle = heading ? heading.textContent.trim() : "";
                if (!fetchedTitle) {
                  throw new Error("Next lesson title was not found");
                }

                nextMain
                  .querySelectorAll(
                    "script, style, link[rel='stylesheet'], " +
                      "[data-bms-term-lookup], [data-bms-lesson-track-nav], " +
                      ".quarto-title-breadcrumbs, .quarto-categories"
                  )
                  .forEach(function (element) {
                    element.remove();
                  });
                nextMain.querySelectorAll(".column-margin").forEach(
                  function (margin) {
                    margin.classList.add("bms-learn-scroll-inline-margin");
                  }
                );

                const prefix = idPrefixForRoute(followingLesson.route);
                rewriteIdReferences(nextMain, prefix);
                rewriteResourceUrls(nextMain, result.finalUrl.href);
                const header = nextMain.querySelector(".quarto-title-block");
                if (header) {
                  header.dataset.bmsLearnScrollLesson = followingLesson.route;
                }

                const fragment = document.createDocumentFragment();
                fragment.appendChild(
                  createDivider(
                    followingLesson,
                    fetchedTitle,
                    startsNewTrack(currentLesson)
                  )
                );
                Array.from(nextMain.children).forEach(function (child) {
                  fragment.appendChild(document.importNode(child, true));
                });
                if (
                  window.BMSLearn &&
                  typeof window.BMSLearn.mountLesson === "function"
                ) {
                  window.BMSLearn.mountLesson(fragment);
                }
                sentinel.replaceWith(fragment);
                tracker.complete(followingLesson.route);
                addSentinel(followingLesson);
              })
              .catch(function () {
                tracker.fail(followingLesson.route);
                sentinel.classList.remove("is-loading");
                sentinel.replaceChildren(
                  createErrorState(followingLesson, attemptLoad)
                );
              });
          }

          observer = new IntersectionObserver(
            function (entries) {
              if (
                entries.some(function (entry) {
                  return entry.isIntersecting;
                })
              ) {
                attemptLoad();
              }
            },
            { rootMargin: "0px 0px 320px 0px" }
          );
          observer.observe(sentinel);
        }

        addSentinel(current);
      })
      .catch(function () {
        // A standalone lesson remains fully usable when the sequence is unavailable.
      });
  }

  const publicApi = {
    createLoadedRouteTracker: createLoadedRouteTracker,
    errorStateForLesson: errorStateForLesson,
    findCurrentLesson: findCurrentLesson,
    idPrefixForRoute: idPrefixForRoute,
    isFinalLesson: isFinalLesson,
    laterLessonRoutes: laterLessonRoutes,
    nextLesson: nextLesson,
    normalizeRoute: normalizeRoute,
    resolveSrcset: resolveSrcset,
    resolveUrlValue: resolveUrlValue,
    rewriteIdReferences: rewriteIdReferences,
    sameOriginUrl: sameOriginUrl,
    startsNewTrack: startsNewTrack
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = publicApi;
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", initializeContinuousLearn);
  }
})();
