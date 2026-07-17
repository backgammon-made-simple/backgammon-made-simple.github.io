from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from PIL import Image
from fontTools.ttLib import TTFont
from playwright.sync_api import Browser, Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = ROOT / "site" / "assets" / "social" / "social-cards.yml"
GENERATED_DIR = ROOT / "site" / "assets" / "social" / "generated"
FONTS_DIR = ROOT / "site" / "assets" / "social" / "fonts"
LOGO_PATH = ROOT / "site" / "assets" / "logo" / "logo-clean.svg"

VARIABLE_FONT_PATH = FONTS_DIR / "SourceSans3-VariableFont_wght.ttf"
REGULAR_FONT_PATH = FONTS_DIR / "SourceSans3-Regular.ttf"
SEMIBOLD_FONT_PATH = FONTS_DIR / "SourceSans3-SemiBold.ttf"

TEMPLATES_DIR = ROOT / "templates" / "social"
HTML_TEMPLATE_PATH = TEMPLATES_DIR / "card.html"
CSS_TEMPLATE_PATH = TEMPLATES_DIR / "social-card.css"

STATE_PATH = GENERATED_DIR / ".render-state.json"
RENDERER_SOURCE_PATH = Path(__file__).resolve()
RENDERER_VERSION = "1.1.0-text-only"

FIELD_ORDER = [
    "slug",
    "kind",
    "width",
    "height",
    "output",
    "title",
    "subtitle",
    "category",
    "visual",
]

ALLOWED_KINDS = {
    "default",
    "github",
    "section",
    "article",
    "tool",
    "benchmark",
}

ALLOWED_CATEGORIES = {
    "",
    "Learn",
    "Analyze",
    "Sage vs GNU",
    "Blog",
    "Research",
    "About",
    "Reference",
    "Open Source",
}

DIMENSIONS = {
    "default": (1200, 630),
    "section": (1200, 630),
    "article": (1200, 630),
    "tool": (1200, 630),
    "benchmark": (1200, 630),
    "github": (1280, 640),
}

TITLE_SIZE_STEPS = {
    "default": [84, 80, 76, 72, 68, 64],
    "github": [82, 78, 74, 70, 66, 62],
    "section": [90, 86, 82, 78, 74, 70, 66],
    "article": [94, 90, 86, 82, 78, 74, 70],
    "tool": [86, 82, 78, 74, 70, 66, 62],
    "benchmark": [88, 84, 80, 76, 72, 68, 64],
}

SUBTITLE_SIZE_STEPS = {
    "default": [36, 34, 32, 30, 28],
    "github": [34, 32, 30, 28, 26],
    "section": [35, 33, 31, 29, 27],
    "article": [36, 34, 32, 30, 28],
    "tool": [34, 32, 30, 28, 26],
    "benchmark": [34, 32, 30, 28, 26],
}

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HTML_PATTERN = re.compile(r"<[^>]+>")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\([^)]+\)")
MARKDOWN_MARKER_PATTERN = re.compile(r"(^|\s)(#{1,6}\s|```|\*\*|__)")

FONT_REGULAR_PLACEHOLDER = "__FONT_REGULAR_DATA_URI__"
FONT_SEMIBOLD_PLACEHOLDER = "__FONT_SEMIBOLD_DATA_URI__"


class ContractError(Exception):
    """Raised when an input or output violates the social-card contract."""


@dataclass(frozen=True)
class Card:
    slug: str
    kind: str
    width: int
    height: int
    output: str
    title: str
    subtitle: str
    category: str
    visual: str

    @property
    def output_path(self) -> Path:
        return (ROOT / PurePosixPath(self.output)).resolve(strict=False)


@dataclass(frozen=True)
class FontFiles:
    regular: Path
    semibold: Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def normalize_string(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def package_version_or_unknown(name: str) -> str:
    try:
        return package_version(name)
    except PackageNotFoundError:
        return "unknown"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_data_uri(path: Path, mime_type: str) -> str:
    require(path.is_file(), f"Missing local asset: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def contains_markup(value: str) -> bool:
    return bool(
        HTML_PATTERN.search(value)
        or MARKDOWN_LINK_PATTERN.search(value)
        or MARKDOWN_MARKER_PATTERN.search(value)
        or "`" in value
    )


def resolve_font_files() -> FontFiles:
    """
    Prefer the original Google Fonts variable TrueType file.

    A static Regular + SemiBold pair is also supported. No system font lookup
    or remote font request is used.
    """
    if VARIABLE_FONT_PATH.is_file():
        return FontFiles(
            regular=VARIABLE_FONT_PATH,
            semibold=VARIABLE_FONT_PATH,
        )

    if REGULAR_FONT_PATH.is_file() and SEMIBOLD_FONT_PATH.is_file():
        return FontFiles(
            regular=REGULAR_FONT_PATH,
            semibold=SEMIBOLD_FONT_PATH,
        )

    raise ContractError(
        "Missing Source Sans 3 TrueType fonts.\n"
        "Use either:\n"
        f"- {VARIABLE_FONT_PATH}\n"
        "or both:\n"
        f"- {REGULAR_FONT_PATH}\n"
        f"- {SEMIBOLD_FONT_PATH}"
    )



def validate_generated_directory() -> Path:
    """
    Resolve the generated directory through every existing symlink and require
    the final location to remain inside the repository.

    This catches a symlink on `generated` itself as well as a symlink on any
    existing parent directory.
    """
    repository_root = ROOT.resolve(strict=True)
    generated_root = GENERATED_DIR.resolve(strict=False)

    try:
        generated_root.relative_to(repository_root)
    except ValueError as exc:
        raise ContractError(
            "The generated social directory resolves outside the repository: "
            f"{GENERATED_DIR} -> {generated_root}"
        ) from exc

    return generated_root


def load_font_codepoints(path: Path) -> set[int]:
    """Read the Unicode cmap from a pinned local TrueType font."""
    try:
        font = TTFont(path, lazy=True)
        try:
            cmap = font.getBestCmap() or {}
            return set(cmap.keys())
        finally:
            font.close()
    except Exception as exc:
        raise ContractError(f"Could not read local font '{path}': {exc}") from exc


def required_codepoints(text: str) -> set[int]:
    """
    Return visible Unicode codepoints that must be supplied by the local font.

    Whitespace and control characters do not require a visible glyph.
    """
    return {
        ord(character)
        for character in text
        if not character.isspace()
        and not unicodedata.category(character).startswith("C")
    }


def describe_codepoints(codepoints: set[int]) -> str:
    values = []
    for codepoint in sorted(codepoints):
        character = chr(codepoint)
        values.append(f"U+{codepoint:04X} {character!r}")
    return ", ".join(values)


def validate_font_coverage(cards: list[Card], fonts: FontFiles) -> None:
    """
    Ensure every displayed character exists in the pinned local font files.

    This prevents Chromium from silently substituting a system font for a
    missing title, category, brand, or subtitle glyph.
    """
    semibold_text = "Backgammon Made Simple" + "".join(
        card.title + card.category for card in cards
    )
    regular_text = "".join(card.subtitle for card in cards)

    semibold_missing = (
        required_codepoints(semibold_text)
        - load_font_codepoints(fonts.semibold)
    )
    regular_missing = (
        required_codepoints(regular_text)
        - load_font_codepoints(fonts.regular)
    )

    if semibold_missing:
        raise ContractError(
            "The pinned semibold font is missing required glyphs: "
            + describe_codepoints(semibold_missing)
        )

    if regular_missing:
        raise ContractError(
            "The pinned regular font is missing required glyphs: "
            + describe_codepoints(regular_missing)
        )

def validate_required_resources() -> FontFiles:
    required = [
        MANIFEST_PATH,
        HTML_TEMPLATE_PATH,
        CSS_TEMPLATE_PATH,
        LOGO_PATH,
    ]

    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ContractError(
            "Missing required local files:\n- " + "\n- ".join(missing)
        )

    validate_generated_directory()
    return resolve_font_files()


def validate_output_path(card: Card) -> None:
    output = card.output

    require("\x00" not in output, f"Null byte in output path: {output}")
    require("://" not in output, f"URL scheme in output path: {output}")
    require("\\" not in output, f"Output path must use '/': {output}")
    require(output.endswith(".png"), f"Output must end in .png: {output}")

    pure = PurePosixPath(output)
    require(not pure.is_absolute(), f"Output must be repository-relative: {output}")
    require(
        all(part not in {".", ".."} for part in pure.parts),
        f"Output contains an unsafe path segment: {output}",
    )

    if card.kind == "github":
        expected = f"site/assets/social/generated/{card.slug}.png"
    elif card.slug == "social-default":
        require(
            card.kind == "default",
            "The social-default card must use kind: default",
        )
        expected = "site/assets/social/generated/social-default.png"
    else:
        expected = f"site/assets/social/generated/social-{card.slug}.png"

    require(
        output == expected,
        (
            f"Output mapping mismatch for '{card.slug}': "
            f"got '{output}', expected '{expected}'"
        ),
    )

    generated_root = validate_generated_directory()
    try:
        card.output_path.relative_to(generated_root)
    except ValueError as exc:
        raise ContractError(
            f"Output escapes site/assets/social/generated/: {output}"
        ) from exc


def validate_card(card: Card) -> None:
    require(
        SLUG_PATTERN.fullmatch(card.slug) is not None,
        f"Invalid slug: {card.slug}",
    )
    require(card.kind in ALLOWED_KINDS, f"Unknown kind: {card.kind}")

    if card.kind == "github":
        require(
            card.slug.startswith("github-"),
            f"GitHub card slug must begin with 'github-': {card.slug}",
        )

    expected_dimensions = DIMENSIONS[card.kind]
    require(
        (card.width, card.height) == expected_dimensions,
        (
            f"Wrong dimensions for '{card.slug}': "
            f"got {card.width}x{card.height}, "
            f"expected {expected_dimensions[0]}x{expected_dimensions[1]}"
        ),
    )

    validate_output_path(card)

    require(card.title.strip() != "", f"Blank title for '{card.slug}'")
    require(
        not contains_markup(card.title),
        f"Title contains HTML or Markdown for '{card.slug}'",
    )
    require(
        not contains_markup(card.subtitle),
        f"Subtitle contains HTML or Markdown for '{card.slug}'",
    )
    require(
        card.category in ALLOWED_CATEGORIES,
        f"Unknown category for '{card.slug}': {card.category!r}",
    )

    # The field remains required to preserve the closed nine-field schema.
    # The text-only system intentionally accepts only an empty string.
    require(
        card.visual == "",
        (
            f"Text-only renderer requires visual: \"\" for '{card.slug}'. "
            f"Received {card.visual!r}"
        ),
    )


def parse_card(item: dict[str, Any], index: int) -> Card:
    require(
        list(item.keys()) == FIELD_ORDER,
        (
            f"Card #{index} must contain exactly the nine fields "
            "in contract order"
        ),
    )

    for key, value in item.items():
        if key in {"width", "height"}:
            require(
                isinstance(value, int) and not isinstance(value, bool),
                (
                    f"Card #{index} field '{key}' must be an integer, "
                    "not Boolean"
                ),
            )
        else:
            require(
                isinstance(value, str),
                f"Card #{index} field '{key}' must be a string",
            )

    card = Card(
        slug=normalize_string(item["slug"]),
        kind=normalize_string(item["kind"]),
        width=item["width"],
        height=item["height"],
        output=normalize_string(item["output"]),
        title=normalize_string(item["title"]),
        subtitle=normalize_string(item["subtitle"]),
        category=normalize_string(item["category"]),
        visual=normalize_string(item["visual"]),
    )

    validate_card(card)
    return card


def load_manifest() -> list[Card]:
    try:
        raw = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractError(f"Malformed YAML: {exc}") from exc

    require(isinstance(raw, dict), "Manifest root must be a mapping")
    require(
        set(raw.keys()) == {"cards"},
        "Manifest must contain exactly one top-level key: cards",
    )
    require(isinstance(raw["cards"], list), "cards must be a list")

    cards: list[Card] = []
    seen_slugs: set[str] = set()
    seen_outputs: set[str] = set()

    for index, item in enumerate(raw["cards"], start=1):
        require(isinstance(item, dict), f"Card #{index} must be a mapping")
        card = parse_card(item, index)

        require(card.slug not in seen_slugs, f"Duplicate slug: {card.slug}")
        require(card.output not in seen_outputs, f"Duplicate output: {card.output}")

        seen_slugs.add(card.slug)
        seen_outputs.add(card.output)
        cards.append(card)

    return cards


def manifest_warnings(cards: list[Card]) -> list[str]:
    warnings: list[str] = []
    seen_visible: dict[tuple[str, str], str] = {}

    for card in cards:
        visible = (card.title, card.subtitle)
        previous = seen_visible.get(visible)
        if previous:
            warnings.append(
                f"'{card.slug}' and '{previous}' share the same title and subtitle"
            )
        else:
            seen_visible[visible] = card.slug

        if card.subtitle and len(card.subtitle) > 140:
            warnings.append(
                f"'{card.slug}' subtitle exceeds the recommended 140 characters"
            )

        if "\n" not in card.title and len(card.title) > 42:
            warnings.append(
                f"'{card.slug}' has a long title without an intentional line break"
            )

    return warnings


def load_css_inline(fonts: FontFiles) -> str:
    css = CSS_TEMPLATE_PATH.read_text(encoding="utf-8")

    require(
        FONT_REGULAR_PLACEHOLDER in css,
        f"CSS is missing {FONT_REGULAR_PLACEHOLDER}",
    )
    require(
        FONT_SEMIBOLD_PLACEHOLDER in css,
        f"CSS is missing {FONT_SEMIBOLD_PLACEHOLDER}",
    )

    css = css.replace(
        FONT_REGULAR_PLACEHOLDER,
        make_data_uri(fonts.regular, "font/ttf"),
    )
    css = css.replace(
        FONT_SEMIBOLD_PLACEHOLDER,
        make_data_uri(fonts.semibold, "font/ttf"),
    )

    require("__FONT_" not in css, "One or more font placeholders were not replaced")
    return css


def load_template() -> Any:
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return environment.get_template(HTML_TEMPLATE_PATH.name)


def build_html(template: Any, card: Card, css_inline: str) -> str:
    return template.render(
        card=card,
        css_inline=css_inline,
        logo_data_uri=make_data_uri(LOGO_PATH, "image/svg+xml"),
    )


def create_page(browser: Browser, card: Card) -> tuple[Any, Page, list[str]]:
    remote_requests: list[str] = []

    context = browser.new_context(
        viewport={"width": card.width, "height": card.height},
        device_scale_factor=1,
        locale="en-US",
        timezone_id="UTC",
        color_scheme="light",
        reduced_motion="reduce",
    )

    context.route(
        re.compile(r"^https?://"),
        lambda route: route.abort(),
    )

    page = context.new_page()
    page.on(
        "request",
        lambda request: (
            remote_requests.append(request.url)
            if request.url.startswith(("http://", "https://"))
            else None
        ),
    )
    page.emulate_media(
        media="screen",
        color_scheme="light",
        reduced_motion="reduce",
    )

    return context, page, remote_requests


def wait_for_assets(page: Page, remote_requests: list[str]) -> None:
    result = page.evaluate(
        """
        async () => {
          const images = Array.from(document.images);

          let imageError = null;
          try {
            await Promise.all(
              images.map(async image => {
                if (image.complete && image.naturalWidth > 0) {
                  return;
                }
                await image.decode();
              })
            );
          } catch (error) {
            imageError = String(error);
          }

          let fontError = null;
          try {
            await Promise.all([
              document.fonts.load(
                '400 16px "Source Sans 3 Local"',
                "Backgammon Made Simple"
              ),
              document.fonts.load(
                '600 16px "Source Sans 3 Local"',
                "Backgammon Made Simple"
              )
            ]);
            await document.fonts.ready;
          } catch (error) {
            fontError = String(error);
          }

          return {
            imageError,
            images: images.map(image => ({
              complete: image.complete,
              naturalWidth: image.naturalWidth,
              naturalHeight: image.naturalHeight
            })),
            fontError,
            regularLoaded: document.fonts.check(
              '400 16px "Source Sans 3 Local"',
              "Backgammon"
            ),
            semiboldLoaded: document.fonts.check(
              '600 16px "Source Sans 3 Local"',
              "Backgammon"
            )
          };
        }
        """
    )

    require(
        not remote_requests,
        "Remote network requests are forbidden:\n- " + "\n- ".join(remote_requests),
    )
    require(
        result["imageError"] is None
        and all(
            image["complete"]
            and image["naturalWidth"] > 0
            and image["naturalHeight"] > 0
            for image in result["images"]
        ),
        f"Embedded logo failed to load: {json.dumps(result, indent=2)}",
    )
    require(
        result["fontError"] is None
        and result["regularLoaded"]
        and result["semiboldLoaded"],
        f"Source Sans 3 failed to load: {json.dumps(result, indent=2)}",
    )

    page.evaluate(
        """
        () => new Promise(resolve => {
          requestAnimationFrame(() => requestAnimationFrame(resolve));
        })
        """
    )


def fit_text(page: Page, card: Card) -> list[str]:
    result = page.evaluate(
        """
        ({ titleSteps, subtitleSteps }) => {
          const title = document.querySelector(".title");
          const subtitle = document.querySelector(".subtitle");
          const stack = document.querySelector(".content-stack");
          const main = document.querySelector(".card-main");
          const footer = document.querySelector(".footer-accent");
          const slot = document.querySelector(".nav-pill-slot");
          const pill = document.querySelector(".nav-pill");

          const tolerance = 2;

          const countLines = element => {
            if (!element || !element.textContent.trim()) {
              return 0;
            }

            const range = document.createRange();
            range.selectNodeContents(element);

            const tops = [];
            for (const rect of Array.from(range.getClientRects())) {
              if (rect.width <= 0 || rect.height <= 0) {
                continue;
              }

              if (!tops.some(top => Math.abs(top - rect.top) <= tolerance)) {
                tops.push(rect.top);
              }
            }

            return Math.max(1, tops.length);
          };

          const horizontalFits = element => (
            !element ||
            element.scrollWidth <= element.clientWidth + tolerance
          );

          const layoutFits = () => {
            const stackRect = stack.getBoundingClientRect();
            const mainRect = main.getBoundingClientRect();
            const footerRect = footer.getBoundingClientRect();

            return (
              stackRect.left >= mainRect.left - tolerance &&
              stackRect.right <= mainRect.right + tolerance &&
              stackRect.bottom <= footerRect.top - 14 + tolerance
            );
          };

          if (
            pill &&
            slot &&
            pill.scrollWidth > slot.clientWidth + tolerance
          ) {
            return { ok: false, reason: "category overflow" };
          }

          let chosenTitle = null;
          let chosenSubtitle = subtitle ? null : 0;

          outer:
          for (const titleSize of titleSteps) {
            title.style.fontSize = `${titleSize}px`;
            void title.offsetHeight;

            if (!horizontalFits(title) || countLines(title) > 3) {
              continue;
            }

            if (!subtitle) {
              if (layoutFits()) {
                chosenTitle = titleSize;
                chosenSubtitle = 0;
                break;
              }
              continue;
            }

            for (const subtitleSize of subtitleSteps) {
              subtitle.style.fontSize = `${subtitleSize}px`;
              void subtitle.offsetHeight;

              if (
                horizontalFits(subtitle) &&
                countLines(subtitle) <= 3 &&
                layoutFits()
              ) {
                chosenTitle = titleSize;
                chosenSubtitle = subtitleSize;
                break outer;
              }
            }
          }

          if (chosenTitle === null) {
            return {
              ok: false,
              reason: subtitle
                ? "title/subtitle combination does not fit"
                : "title does not fit"
            };
          }

          return {
            ok: true,
            titleSize: chosenTitle,
            subtitleSize: chosenSubtitle,
            titleAtMinimum:
              chosenTitle === titleSteps[titleSteps.length - 1],
            subtitleAtMinimum:
              Boolean(subtitle) &&
              chosenSubtitle === subtitleSteps[subtitleSteps.length - 1]
          };
        }
        """,
        {
            "titleSteps": TITLE_SIZE_STEPS[card.kind],
            "subtitleSteps": SUBTITLE_SIZE_STEPS[card.kind],
        },
    )

    if not result.get("ok", False):
        raise ContractError(
            f"Text fit failed for '{card.slug}': "
            f"{result.get('reason', 'unknown layout failure')}"
        )

    warnings: list[str] = []

    if result.get("titleAtMinimum"):
        warnings.append(
            f"'{card.slug}' title required the minimum supported font size"
        )

    if result.get("subtitleAtMinimum"):
        warnings.append(
            f"'{card.slug}' subtitle required the minimum supported font size"
        )

    return warnings


def prepare_page(
    browser: Browser,
    template: Any,
    css_inline: str,
    card: Card,
) -> tuple[Any, Page]:
    context, page, remote_requests = create_page(browser, card)

    try:
        page.set_content(
            build_html(template, card, css_inline),
            wait_until="load",
        )
        wait_for_assets(page, remote_requests)
        return context, page
    except Exception:
        context.close()
        raise


def browser_validate_card(
    browser: Browser,
    template: Any,
    css_inline: str,
    card: Card,
) -> list[str]:
    context, page = prepare_page(browser, template, css_inline, card)

    try:
        return fit_text(page, card)
    finally:
        context.close()


def post_render_validate(card: Card) -> None:
    require(
        card.output_path.is_file(),
        f"Missing PNG after render: {card.output}",
    )

    try:
        with Image.open(card.output_path) as image:
            image.load()
            require(image.format == "PNG", f"Output is not PNG: {card.output}")
            require(
                image.size == (card.width, card.height),
                (
                    f"Wrong PNG dimensions for '{card.output}': "
                    f"got {image.size[0]}x{image.size[1]}, "
                    f"expected {card.width}x{card.height}"
                ),
            )
    except OSError as exc:
        raise ContractError(f"Unreadable PNG: {card.output}") from exc


def render_card(
    browser: Browser,
    template: Any,
    css_inline: str,
    card: Card,
) -> list[str]:
    context, page = prepare_page(browser, template, css_inline, card)

    try:
        warnings = fit_text(page, card)

        card.output_path.parent.mkdir(parents=True, exist_ok=True)
        locator = page.locator(".social-card")

        require(
            locator.count() == 1,
            f"Expected exactly one .social-card for '{card.slug}'",
        )

        locator.screenshot(
            path=str(card.output_path),
            animations="disabled",
            caret="hide",
        )
    finally:
        context.close()

    post_render_validate(card)
    return warnings


def render_state_hash(
    card: Card,
    chromium_version: str,
    fonts: FontFiles,
) -> str:
    payload = {
        "renderer_version": RENDERER_VERSION,
        "renderer_source_sha256": sha256_bytes(
            RENDERER_SOURCE_PATH.read_bytes()
        ),
        "python_packages": {
            "jinja2": package_version_or_unknown("Jinja2"),
            "pyyaml": package_version_or_unknown("PyYAML"),
            "pillow": package_version_or_unknown("Pillow"),
            "playwright": package_version_or_unknown("playwright"),
        },
        "chromium_version": chromium_version,
        "card": asdict(card),
        "html_sha256": sha256_bytes(HTML_TEMPLATE_PATH.read_bytes()),
        "css_sha256": sha256_bytes(CSS_TEMPLATE_PATH.read_bytes()),
        "logo_sha256": sha256_bytes(LOGO_PATH.read_bytes()),
        "regular_font_sha256": sha256_bytes(fonts.regular.read_bytes()),
        "semibold_font_sha256": sha256_bytes(fonts.semibold.read_bytes()),
        "viewport": [card.width, card.height],
        "device_scale_factor": 1,
        "locale": "en-US",
        "timezone": "UTC",
        "media": "screen",
        "color_scheme": "light",
        "reduced_motion": "reduce",
        "screenshot_target": ".social-card",
        "screenshot_animations": "disabled",
        "screenshot_caret": "hide",
    }

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def load_state() -> dict[str, str]:
    if not STATE_PATH.is_file():
        return {}

    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Malformed render state: {STATE_PATH}") from exc

    require(isinstance(raw, dict), "Render state must be a JSON object")
    return {str(key): str(value) for key, value in raw.items()}


def save_state(state: dict[str, str]) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def clean_orphans(cards: list[Card]) -> None:
    expected = {card.output_path for card in cards}

    if not GENERATED_DIR.exists():
        return

    for path in sorted(GENERATED_DIR.glob("*.png")):
        if path.resolve() not in expected:
            print(f"Deleting orphan: {path.relative_to(ROOT)}")
            path.unlink()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render text-only Backgammon Made Simple social cards"
    )

    commands = parser.add_mutually_exclusive_group()
    commands.add_argument("--validate-only", action="store_true")
    commands.add_argument("--all", action="store_true")
    commands.add_argument("--changed", action="store_true")
    commands.add_argument("--slug", metavar="SLUG")
    commands.add_argument("--clean-orphans", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    fonts = validate_required_resources()
    all_cards = load_manifest()
    validate_font_coverage(all_cards, fonts)

    for warning in manifest_warnings(all_cards):
        print(f"Warning: {warning}")

    if args.clean_orphans:
        clean_orphans(all_cards)
        return 0

    selected_cards = all_cards
    if args.slug:
        selected_cards = [card for card in all_cards if card.slug == args.slug]
        require(
            len(selected_cards) == 1,
            f"No card found for slug: {args.slug}",
        )

    mode = "changed"
    if args.validate_only:
        mode = "validate"
    elif args.all:
        mode = "all"
    elif args.slug:
        mode = "slug"

    css_inline = load_css_inline(fonts)
    template = load_template()
    state = load_state()
    new_state = dict(state)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        try:
            chromium_version = str(browser.version)

            if mode == "validate":
                for card in selected_cards:
                    warnings = browser_validate_card(
                        browser,
                        template,
                        css_inline,
                        card,
                    )
                    for warning in warnings:
                        print(f"Warning: {warning}")
                    print(f"Validated: {card.slug}")

                print("Social-card renderer validation passed")
                return 0

            for card in selected_cards:
                current_hash = render_state_hash(
                    card,
                    chromium_version,
                    fonts,
                )

                if (
                    mode == "changed"
                    and card.output_path.is_file()
                    and state.get(card.output) == current_hash
                ):
                    print(f"Unchanged: {card.output}")
                    continue

                warnings = render_card(
                    browser,
                    template,
                    css_inline,
                    card,
                )

                for warning in warnings:
                    print(f"Warning: {warning}")

                new_state[card.output] = current_hash
                print(f"Rendered: {card.output}")

        finally:
            browser.close()

    save_state(new_state)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("Cancelled", file=sys.stderr)
        raise SystemExit(130)
