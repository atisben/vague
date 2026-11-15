"""Regex detector for AI-design tells in UI source files, one file at a time.

Rules ported from pbakaus/impeccable@2b86d9c (Apache-2.0), `crates/detect/src/regex_matchers.rs`.

Upstream reads one line at a time and then widens to the enclosing CSS block or
markup tag to decide. This port keeps that two-step shape: a regex finds a
candidate anywhere in the file, and an `accept` check reads the candidate's
scope. Where upstream cannot see the scope it fails safe to reporting; this port
fails safe to silence, because a noisy detector gets ignored.

Rules that need rendered or computed styles (contrast, tiny text, overflow) are
out of reach of a single-file regex and are not ported.
"""

from __future__ import annotations

import json
import os
import re
import sys
from bisect import bisect_right
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import typer

from vague.git import get_scope
from vague.hooks import edited_file
from vague.log import get_logger
from vague.memory import search

STYLE_EXTENSIONS = frozenset({
    ".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro",
})
# Plain .js/.ts hold CSS-in-JS and style objects, which the property rules read safely.
# Markup rules need a real tag around the match: in a plain script a `<img` or a class
# list is usually a string being assembled, so a missing attribute proves nothing.
MARKUP_EXTENSIONS = STYLE_EXTENSIONS - {".js", ".ts"}
UI_EXTENSIONS = STYLE_EXTENSIONS
# Files where prose and code samples sit beside real styles: a CSS property only counts
# inside a <style> block, a <script> block or a style attribute, never in rendered text.
HTML_LIKE_EXTENSIONS = frozenset({".html", ".htm", ".vue", ".svelte", ".astro"})
CSS_COMMENT_EXTENSIONS = HTML_LIKE_EXTENSIONS | {".css", ".scss", ".sass", ".less"}

OVERUSED_FONTS = (
    "Inter", "Roboto", "Open Sans", "Lato", "Montserrat", "Arial", "Helvetica", "Fraunces", "Geist Sans",
    "Geist Mono", "Geist", "Mona Sans", "Plus Jakarta Sans", "Space Grotesk", "Recoleta", "Instrument Sans",
    "Instrument Serif",
)
_OVERUSED_LOWER = {name.lower(): name for name in OVERUSED_FONTS}

NEUTRAL_COLOR_KEYWORDS = frozenset({
    "transparent", "currentcolor", "black", "white", "gray", "grey", "silver", "dimgray", "dimgrey", "darkgray",
    "darkgrey", "lightgray", "lightgrey", "gainsboro", "whitesmoke",
})

_SCOPE_LIMIT = 4_000


@dataclass(frozen=True)
class Finding:
    rule_id: str
    line: int
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class Context:
    text: str
    suffix: str
    brand_fonts: frozenset[str] = frozenset()


def _always(match: re.Match[str], ctx: Context) -> bool:
    return True


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]
    message: str
    extensions: frozenset[str]
    accept: Callable[[re.Match[str], Context], bool] = field(default=_always)
    evidence: Callable[[re.Match[str], Context], str] | None = None
    # Where a match must sit to count: a style carrier, a class list inside a tag, or a tag itself.
    carrier: Literal["style", "class", "tag"] = "style"


# ─── Scope readers ───────────────────────────────────────────────────────────


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return start, len(text) if end == -1 else end


def _line_at(text: str, pos: int) -> str:
    start, end = _line_bounds(text=text, pos=pos)
    return text[start:end]


def _tag_span(text: str, pos: int) -> tuple[int, int] | None:
    """The markup tag `pos` sits inside, or None when it sits in text or a stylesheet."""
    lt = text.rfind("<", max(0, pos - _SCOPE_LIMIT), pos)
    if lt == -1 or text.rfind(">", lt, pos) != -1 or not re.match(r"<[A-Za-z]", text[lt:lt + 2]):
        return None
    gt = text.find(">", pos, pos + _SCOPE_LIMIT)
    return (lt, gt + 1) if gt != -1 else None


def _brace_span(text: str, pos: int) -> tuple[int, int] | None:
    """The innermost `{ ... }` block around `pos`: a CSS rule or a style object."""
    depth, start = 0, -1
    for i in range(pos - 1, max(-1, pos - _SCOPE_LIMIT), -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                start = i
                break
            depth -= 1
    if start == -1:
        return None
    depth = 0
    for i in range(pos, min(len(text), pos + _SCOPE_LIMIT)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            if depth == 0:
                return start, i + 1
            depth -= 1
    return None


def _style_span(text: str, pos: int) -> tuple[int, int] | None:
    """A declaration's scope: its `style="..."` tag, else its CSS block or style object."""
    return _tag_span(text=text, pos=pos) or _brace_span(text=text, pos=pos)


def _tag_scope(text: str, pos: int) -> str | None:
    span = _tag_span(text=text, pos=pos)
    return text[span[0]:span[1]] if span else None


def _style_scope(text: str, pos: int) -> str | None:
    span = _style_span(text=text, pos=pos)
    return text[span[0]:span[1]] if span else None


def _class_scope(text: str, pos: int) -> str:
    """A utility class's scope: its tag, else its line (a class string outside markup)."""
    return _tag_scope(text=text, pos=pos) or _line_at(text=text, pos=pos)


_RADIUS_DECL_RE = re.compile(
    r"(?i)(?:border-radius|border-(?:top|bottom|start|end)-(?:left|right|start|end)-radius|"
    r"border(?:Top|Bottom)?(?:Left|Right)?Radius)\s*:\s*([^;}\n]+)"
)
_ZERO_RADIUS_RE = re.compile(r"(?i)\s*['\"`]?\s*(?:(?:0(?:px|rem|em|%)?|none)\s*)+['\"`]?\s*,?\s*")
_ROUNDED_RE = re.compile(r"(?<![\w-])rounded(?:-(?:xs|sm|md|lg|xl|2xl|3xl|4xl|full|\[[^\]]+\]))?(?![\w-])")


def _declares_radius(scope: str) -> bool:
    return any(not _ZERO_RADIUS_RE.fullmatch(m.group(1)) for m in _RADIUS_DECL_RE.finditer(scope))


def _has_rounded_class(scope: str) -> bool:
    return bool(_ROUNDED_RE.search(scope))


def _hex_channels(color: str) -> tuple[int, int, int] | None:
    m = re.fullmatch(r"#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})(?:[0-9a-f]{2})?", color)
    if m:
        return int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
    m = re.fullmatch(r"#([0-9a-f])([0-9a-f])([0-9a-f])[0-9a-f]?", color)
    if m:
        return int(m.group(1) * 2, 16), int(m.group(2) * 2, 16), int(m.group(3) * 2, 16)
    return None


def _is_neutral_color(raw: str) -> bool:
    """Gray, black, white or transparent: a hairline divider, not an accent (channel spread under 30)."""
    color = raw.strip().strip("'\"`").strip().lower()
    if not color:
        return False
    if color in NEUTRAL_COLOR_KEYWORDS:
        return True
    rgb = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+).*\)", color)
    channels = tuple(int(v) for v in rgb.groups()) if rgb else _hex_channels(color=color)
    return channels is not None and max(channels) - min(channels) < 30


def _first_color_token(rest: str) -> str:
    m = re.match(r"\s*((?:[a-z-]+\([^)]*\))|#[0-9a-fA-F]{3,8}\b|[a-zA-Z]+)", rest)
    return m.group(1) if m else ""


def _in_state_variant(scope: str, start: int) -> bool:
    """`hover:bg-blue-600` paints only on hover, so it says nothing about the resting colors."""
    token_start = max(scope.rfind(" ", 0, start), scope.rfind('"', 0, start), scope.rfind("'", 0, start)) + 1
    prefix = scope[token_start:start]
    return bool(re.search(r"(?:^|:|-)(?:hover|focus|active|visited|disabled|focus-within|focus-visible|checked):",
                          prefix))


_SAFE_ELEMENT_RE = re.compile(r"(?i)<(?:blockquote|nav|pre|code|a|input|span)[\s>]")


# ─── side-tab and border-accent-on-rounded ───────────────────────────────────


_SIDE_TAB_CSS_RE = re.compile(
    r"(?i)(?<![\w-])border-(?:left|right|inline-start|inline-end)\s*:\s*(\d+)px\s+solid\b([^;}\"'\n]*)"
)
_SIDE_TAB_WIDTH_RE = re.compile(r"(?i)(?<![\w-])border-(?:left|right|inline-start|inline-end)-width\s*:\s*(\d+)px")
_SIDE_TAB_JS_RE = re.compile(r"border(?:Left|Right|InlineStart|InlineEnd)\s*[:=]\s*[\"'`](\d+)px\s+solid([^\"'`]*)")
_SIDE_TAB_TW_RE = re.compile(r"(?<![\w-])border-[lrse]-(\d+)(?![\w-])")
_BORDER_ACCENT_CSS_RE = re.compile(r"(?i)(?<![\w-])border-(?:top|bottom)\s*:\s*(\d+)px\s+solid\b([^;}\"'\n]*)")
_BORDER_ACCENT_TW_RE = re.compile(r"(?<![\w-])border-[tb]-(\d+)(?![\w-])")


def _declared_accent(min_width: int) -> Callable[[re.Match[str], Context], bool]:
    """A thick chromatic border declared in a scope that also declares a corner radius."""
    def accept(match: re.Match[str], ctx: Context) -> bool:
        if int(match.group(1)) < min_width:
            return False
        if match.lastindex and match.lastindex >= 2 and _is_neutral_color(_first_color_token(match.group(2))):
            return False
        if _SAFE_ELEMENT_RE.search(_line_at(text=ctx.text, pos=match.start())):
            return False
        scope = _style_scope(text=ctx.text, pos=match.start())
        return scope is not None and _declares_radius(scope=scope)
    return accept


def _class_accent(min_width: int) -> Callable[[re.Match[str], Context], bool]:
    """A `border-l-4` style utility on a tag that is also `rounded`."""
    def accept(match: re.Match[str], ctx: Context) -> bool:
        if int(match.group(1)) < min_width:
            return False
        scope = _tag_scope(text=ctx.text, pos=match.start())
        if scope is None or _SAFE_ELEMENT_RE.match(scope + " "):
            return False
        return _has_rounded_class(scope=scope) and "animate-spin" not in scope
    return accept


# ─── overused-font ───────────────────────────────────────────────────────────


_FONT_ALTERNATION = "|".join(re.escape(name) for name in OVERUSED_FONTS)
_OVERUSED_FONT_RE = re.compile(
    rf"(?i)(?:font-family|fontFamily)\s*:\s*['\"`]?({_FONT_ALTERNATION})(?![\w-])"
)
_GOOGLE_FONTS_URL_RE = re.compile(r"(?i)fonts\.googleapis\.com/css2?\?[^\"'\s)<>]*")


def _google_families(url: str) -> list[str]:
    """`family=Open+Sans:wght@400|Roboto&family=Inter` → ["Open Sans", "Roboto", "Inter"]."""
    families = []
    for m in re.finditer(r"family=([^&]*)", url):
        for part in m.group(1).split("|"):
            name = part.split(":")[0].replace("+", " ").replace("%20", " ").strip()
            if name:
                families.append(name)
    return families


def _overused_google_family(url: str, brand_fonts: frozenset[str]) -> str:
    for family in _google_families(url=url):
        lower = family.lower()
        if lower in _OVERUSED_LOWER and lower not in brand_fonts:
            return _OVERUSED_LOWER[lower]
    return ""


def _accept_font(match: re.Match[str], ctx: Context) -> bool:
    return match.group(1).lower() not in ctx.brand_fonts


def _accept_google_font(match: re.Match[str], ctx: Context) -> bool:
    return bool(_overused_google_family(url=match.group(0), brand_fonts=ctx.brand_fonts))


def _google_font_evidence(match: re.Match[str], ctx: Context) -> str:
    return f"Google Fonts: {_overused_google_family(url=match.group(0), brand_fonts=ctx.brand_fonts)}"


# ─── gradient-text ───────────────────────────────────────────────────────────


_CLIP_TEXT_RE = re.compile(r"(?i)(?:-webkit-)?background-clip\s*:\s*text(?![\w-])")
_BG_CLIP_TEXT_TW_RE = re.compile(r"(?<![\w-])bg-clip-text(?![\w-])")
_TW_GRADIENT_RE = re.compile(r"(?<![\w-])bg-(?:gradient-to-|linear-|radial|conic)")


def _accept_clip_text(match: re.Match[str], ctx: Context) -> bool:
    span = _style_span(text=ctx.text, pos=match.start())
    if span is None:
        return "gradient" in _line_at(text=ctx.text, pos=match.start()).lower()
    # `-webkit-background-clip` and `background-clip` usually come as a pair: report the block once.
    if _CLIP_TEXT_RE.search(ctx.text, span[0], match.start()):
        return False
    return "gradient" in ctx.text[span[0]:span[1]].lower()


def _accept_tw_clip_text(match: re.Match[str], ctx: Context) -> bool:
    return bool(_TW_GRADIENT_RE.search(_class_scope(text=ctx.text, pos=match.start())))


# ─── gray-on-color and ai-color-palette ──────────────────────────────────────


_GRAY_TEXT_RE = re.compile(r"(?<![\w-])text-(?:gray|slate|zinc|neutral|stone)-(\d+)(?![\w-])")
_CHROMATIC_BG_RE = re.compile(
    r"(?<![\w-])bg-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|"
    r"pink|rose)-(\d+)(?![\w-])"
)
_PURPLE_TEXT_RE = re.compile(r"(?<![\w-])text-(?:purple|violet|indigo)-\d+(?![\w-])")
_HEADING_CTX_RE = re.compile(r"(?i)(?<![\w-])text-[2-9]xl(?![\w-])|<h[1-3][\s>]")
_FROM_PURPLE_RE = re.compile(r"(?<![\w-])from-(?:purple|violet|indigo)-\d+(?![\w-])")
_TO_COLOR_RE = re.compile(r"(?<![\w-])to-(?:purple|violet|indigo|blue|cyan|pink|fuchsia)-\d+(?![\w-])")


def _accept_gray_on_color(match: re.Match[str], ctx: Context) -> bool:
    # Shade 700+ is near-black ink, which reads fine on a mid-tone background.
    if int(match.group(1)) >= 700:
        return False
    scope = _tag_scope(text=ctx.text, pos=match.start())
    if scope is None or _in_state_variant(scope=scope, start=scope.find(match.group(0))):
        return False
    # A ternary puts the two classes in exclusive arms; upstream splits the arms, this port stays silent.
    if re.search(r"\?[^:]*:", scope) and "{" in scope:
        return False
    for bg in _CHROMATIC_BG_RE.finditer(scope):
        if scope[bg.end():bg.end() + 1] == "/" or _in_state_variant(scope=scope, start=bg.start()):
            continue
        # 50 and 100 are pale tints that keep gray text readable.
        if bg.group(1) not in ("50", "100"):
            return True
    return False


def _accept_purple_heading(match: re.Match[str], ctx: Context) -> bool:
    return bool(_HEADING_CTX_RE.search(_class_scope(text=ctx.text, pos=match.start())))


def _accept_purple_gradient(match: re.Match[str], ctx: Context) -> bool:
    return bool(_TO_COLOR_RE.search(_class_scope(text=ctx.text, pos=match.start())))


# ─── bounce-easing ───────────────────────────────────────────────────────────


_ANIMATE_BOUNCE_RE = re.compile(r"(?<![\w-])animate-bounce(?![\w-])")
_ANIMATION_BOUNCE_RE = re.compile(
    r"(?i)(?<![\w-])animation(?:-name)?\s*:\s*([^;{}\n]*(?:bounce|elastic|wobble|jiggle|spring)[^;{}\n]*)"
)
_CUBIC_BEZIER_RE = re.compile(
    r"cubic-bezier\(\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\)"
)


def _accept_overshoot(match: re.Match[str], ctx: Context) -> bool:
    """A y control point outside [-0.1, 1.1] overshoots the target and springs back."""
    try:
        y1, y2 = float(match.group(2)), float(match.group(4))
    except ValueError:
        return False
    return not (-0.1 <= y1 <= 1.1 and -0.1 <= y2 <= 1.1)


# ─── broken-image ────────────────────────────────────────────────────────────


_IMG_TAG_RE = re.compile(r"(?i)<img(?![\w-])[^>]*>")
_ATTR_RE = re.compile(r"""([^\s=/>"'{}]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s>]+))?""")


def _names_image_source(name: str) -> bool:
    """`src`, `srcset`, `ngSrc`, a binding of one (`:src`, `v-bind:src`, `bind:src`, `[src]`), or `data-src`."""
    bare = name.lower()
    if bare.startswith("[") and bare.endswith("]"):
        bare = bare[1:-1].removeprefix("attr.")
    bare = bare.split(":")[-1].split(".")[0].removeprefix("data-")
    return bare in ("src", "srcset", "ngsrc")


def _accept_broken_image(match: re.Match[str], ctx: Context) -> bool:
    tag = match.group(0)
    # An expression, spread or template placeholder can supply the source at runtime.
    if "{" in tag or "<%" in tag:
        return False
    for attr in _ATTR_RE.finditer(tag[4:]):
        name, raw = attr.group(1), attr.group(2)
        if not _names_image_source(name=name):
            continue
        if raw is None:
            # Svelte `bind:src` alone is shorthand for `bind:src={src}`; a bare `src` is still empty.
            if ":" in name:
                return False
            continue
        value = raw.strip("\"'").strip()
        if value and value != "#":
            return False
    return True


def _broken_image_evidence(match: re.Match[str], ctx: Context) -> str:
    return " ".join(match.group(0).split())


# ─── The rule list ───────────────────────────────────────────────────────────


_SIDE_TAB_MSG = ("thick colored stripe on one side of a rounded card, the most recognizable AI tell; "
                 "remove it or use a full hairline border or a background tint")
_BORDER_ACCENT_MSG = "thick accent border on a rounded card clashes with the corners; remove the border or the radius"
_FONT_MSG = ("overused default face; choose one with character, or name it in the brief's design-type "
             "learning if it is the brand font")
_GRADIENT_TEXT_MSG = "gradient-filled text is decoration, not meaning; use a solid text color"
_BOUNCE_MSG = "bounce or elastic easing feels dated; use an exponential ease-out (quart, quint or expo)"
_PALETTE_MSG = "purple/indigo is the stock AI palette; use a hue from the brief's design-palette"
_GRAY_MSG = "gray text washes out on a colored background; use a darker shade of the background hue or near-white"
_BROKEN_IMAGE_MSG = "<img> with no usable src ships as a broken box; add a real source or remove the tag"

RULES: list[Rule] = [
    Rule(id="side-tab", pattern=_SIDE_TAB_CSS_RE, message=_SIDE_TAB_MSG, extensions=STYLE_EXTENSIONS,
         accept=_declared_accent(min_width=2)),
    Rule(id="side-tab", pattern=_SIDE_TAB_WIDTH_RE, message=_SIDE_TAB_MSG, extensions=STYLE_EXTENSIONS,
         accept=_declared_accent(min_width=3)),
    Rule(id="side-tab", pattern=_SIDE_TAB_JS_RE, message=_SIDE_TAB_MSG, extensions=STYLE_EXTENSIONS,
         accept=_declared_accent(min_width=3)),
    Rule(id="side-tab", pattern=_SIDE_TAB_TW_RE, message=_SIDE_TAB_MSG, extensions=MARKUP_EXTENSIONS,
         accept=_class_accent(min_width=2), carrier="class"),
    Rule(id="border-accent-on-rounded", pattern=_BORDER_ACCENT_CSS_RE, message=_BORDER_ACCENT_MSG,
         extensions=STYLE_EXTENSIONS, accept=_declared_accent(min_width=3)),
    Rule(id="border-accent-on-rounded", pattern=_BORDER_ACCENT_TW_RE, message=_BORDER_ACCENT_MSG,
         extensions=MARKUP_EXTENSIONS, accept=_class_accent(min_width=1), carrier="class"),
    Rule(id="overused-font", pattern=_OVERUSED_FONT_RE, message=_FONT_MSG, extensions=STYLE_EXTENSIONS,
         accept=_accept_font),
    Rule(id="overused-font", pattern=_GOOGLE_FONTS_URL_RE, message=_FONT_MSG, extensions=STYLE_EXTENSIONS,
         accept=_accept_google_font, evidence=_google_font_evidence),
    Rule(id="gradient-text", pattern=_CLIP_TEXT_RE, message=_GRADIENT_TEXT_MSG, extensions=STYLE_EXTENSIONS,
         accept=_accept_clip_text),
    Rule(id="gradient-text", pattern=_BG_CLIP_TEXT_TW_RE, message=_GRADIENT_TEXT_MSG, extensions=MARKUP_EXTENSIONS,
         accept=_accept_tw_clip_text, carrier="class"),
    Rule(id="gray-on-color", pattern=_GRAY_TEXT_RE, message=_GRAY_MSG, extensions=MARKUP_EXTENSIONS,
         accept=_accept_gray_on_color, carrier="class"),
    Rule(id="ai-color-palette", pattern=_PURPLE_TEXT_RE, message=_PALETTE_MSG, extensions=MARKUP_EXTENSIONS,
         accept=_accept_purple_heading, carrier="class"),
    Rule(id="ai-color-palette", pattern=_FROM_PURPLE_RE, message=_PALETTE_MSG, extensions=MARKUP_EXTENSIONS,
         accept=_accept_purple_gradient, carrier="class"),
    Rule(id="bounce-easing", pattern=_ANIMATE_BOUNCE_RE, message=_BOUNCE_MSG, extensions=STYLE_EXTENSIONS,
         carrier="class"),
    Rule(id="bounce-easing", pattern=_ANIMATION_BOUNCE_RE, message=_BOUNCE_MSG, extensions=STYLE_EXTENSIONS),
    Rule(id="bounce-easing", pattern=_CUBIC_BEZIER_RE, message=_BOUNCE_MSG, extensions=STYLE_EXTENSIONS,
         accept=_accept_overshoot),
    Rule(id="broken-image", pattern=_IMG_TAG_RE, message=_BROKEN_IMAGE_MSG, extensions=MARKUP_EXTENSIONS,
         accept=_accept_broken_image, evidence=_broken_image_evidence, carrier="tag"),
]


# ─── Inline ignores ──────────────────────────────────────────────────────────
# Upstream `inline_ignores.rs`: `impeccable-disable <rules>` waives the rules for the
# whole file, `-disable-line` for its own line, `-disable-next-line` for the next one.
# Rules are comma or space separated, a reason follows `:` or `--`, no rule means all.

_DIRECTIVE_RE = re.compile(r"(?i)impeccable-(disable-next-line|disable-line|disable)\b[ \t]*([^\n\r]*)")
_TRAILING_CLOSER_RE = re.compile(r"\s*(?:\*/\}?|--+>|\*\}|#\}|%>|\}\})\s*$")
_REASON_SEP_RE = re.compile(r"\s*(?:--+|:)\s*")


@dataclass
class _Ignores:
    file: set[str] = field(default_factory=set)
    lines: dict[int, set[str]] = field(default_factory=dict)

    def waives(self, rule_id: str, line: int) -> bool:
        rules = self.file | self.lines.get(line, set())
        return "*" in rules or rule_id in rules


def _parse_rule_list(remainder: str) -> set[str]:
    text = _TRAILING_CLOSER_RE.sub("", remainder).strip()
    sep = _REASON_SEP_RE.search(text)
    if sep:
        text = text[:sep.start()]
    tokens = {t.strip().lower() for t in re.split(r"[\s,]+", text) if t.strip()}
    return {"*"} if not tokens or "*" in tokens else tokens


def _parse_ignores(text: str) -> _Ignores:
    ignores = _Ignores()
    if "impeccable-disable" not in text.lower():
        return ignores
    for number, line in enumerate(text.split("\n"), start=1):
        for m in _DIRECTIVE_RE.finditer(line):
            variant, rules = m.group(1).lower(), _parse_rule_list(remainder=m.group(2))
            if variant == "disable":
                ignores.file |= rules
            else:
                target = number if variant == "disable-line" else number + 1
                ignores.lines.setdefault(target, set()).update(rules)
    return ignores


# ─── Carriers ────────────────────────────────────────────────────────────────


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_EMBEDDED_BLOCK_RE = re.compile(r"(?is)<(style|script)\b[^>]*>.*?</\1\s*>")
_STYLE_ATTR_RE = re.compile(r"""(?i)(?<![\w-])style\s*=\s*(?:"[^"]*"|'[^']*'|\{\{.*?\}\})""", re.DOTALL)


class _Spans:
    """Character ranges, merged where they overlap, with a binary-search membership test."""

    def __init__(self, ranges: list[tuple[int, int]]) -> None:
        merged: list[tuple[int, int]] = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        self.ranges = merged
        self.starts = [start for start, _ in merged]

    def __contains__(self, pos: int) -> bool:
        i = bisect_right(self.starts, pos) - 1
        return i >= 0 and pos < self.ranges[i][1]


@dataclass
class _Carriers:
    comments: _Spans
    style: _Spans | None  # None: the whole file is style text (a stylesheet or a script)
    embedded: _Spans


def _carriers(text: str, suffix: str) -> _Carriers:
    comments = []
    if suffix in HTML_LIKE_EXTENSIONS:
        comments += [m.span() for m in _HTML_COMMENT_RE.finditer(text)]
    if suffix in CSS_COMMENT_EXTENSIONS:
        comments += [m.span() for m in _CSS_COMMENT_RE.finditer(text)]
    if suffix not in HTML_LIKE_EXTENSIONS:
        return _Carriers(comments=_Spans(comments), style=None, embedded=_Spans([]))
    embedded = [m.span() for m in _EMBEDDED_BLOCK_RE.finditer(text)]
    attributes = [m.span() for m in _STYLE_ATTR_RE.finditer(text)]
    return _Carriers(comments=_Spans(comments), style=_Spans(embedded + attributes), embedded=_Spans(embedded))


def _in_carrier(rule: Rule, pos: int, ctx: Context, carriers: _Carriers) -> bool:
    if pos in carriers.comments:
        return False
    if rule.carrier == "style":
        return carriers.style is None or pos in carriers.style
    if ctx.suffix not in MARKUP_EXTENSIONS:
        return True
    # Markup inside a <script> or <style> block is a string or a selector, not a rendered tag.
    # A tag match starts on its own `<`, so look for the tag from just inside it.
    inside = pos + 1 if rule.carrier == "tag" else pos
    return _tag_span(text=ctx.text, pos=inside) is not None and pos not in carriers.embedded


# ─── Public API ──────────────────────────────────────────────────────────────


def scan_text(text: str, suffix: str, brand_fonts: frozenset[str] = frozenset(),
              path: Path | None = None) -> list[Finding]:
    """Run every rule that applies to `suffix` over `text`, one finding per rule and line, in line order."""
    ctx = Context(text=text, suffix=suffix.lower(), brand_fonts=frozenset(f.lower() for f in brand_fonts))
    ignores = _parse_ignores(text=text)
    carriers = _carriers(text=text, suffix=ctx.suffix)
    seen: set[tuple[str, int]] = set()
    findings = []
    for rule in RULES:
        if ctx.suffix not in rule.extensions:
            continue
        for match in rule.pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            if (rule.id, line) in seen or ignores.waives(rule_id=rule.id, line=line):
                continue
            if not _in_carrier(rule=rule, pos=match.start(), ctx=ctx, carriers=carriers) or not rule.accept(match, ctx):
                continue
            seen.add((rule.id, line))
            evidence = rule.evidence(match, ctx) if rule.evidence else " ".join(match.group(0).split())
            findings.append(Finding(rule_id=rule.id, line=line, message=f"{evidence[:80]}: {rule.message}",
                                    path=path))
    return sorted(findings, key=lambda f: (f.line, f.rule_id))


def check(path: Path, brand_fonts: frozenset[str] = frozenset()) -> list[Finding]:
    """Findings for one UI source file. A non-UI, missing, unreadable or binary file yields []. Never raises."""
    try:
        if path.suffix.lower() not in UI_EXTENSIONS:
            return []
        raw = path.read_bytes()
        if b"\x00" in raw:
            return []
        text = raw.decode("utf-8")
        return scan_text(text=text, suffix=path.suffix, brand_fonts=brand_fonts, path=path)
    except Exception:  # noqa: BLE001 - a detector run from a hook must never break the caller
        return []


_BRAND_PREFIX_RE = re.compile(r"(?i)brand fonts?\s*:")
_FAMILY_RE = re.compile(r"[A-ZÀ-Þ][\wÀ-ÿ]*(?:[ -][A-ZÀ-Þ][\wÀ-ÿ]*)*")


def parse_brand_fonts(text: str | None) -> frozenset[str]:
    """Lower-cased family names from a `design-type` learning, e.g.

    `Brand fonts: Fraunces (display, 600) and Inter (body 400). JetBrains Mono 400 for SKUs.`
    → {"fraunces", "inter", "jetbrains mono"}.

    Parenthesised details are dropped. The text after `Brand fonts:` splits into clauses at
    sentence ends, commas, semicolons and "and"; each clause's leading run of capitalised
    words is a family. A sentence that does not open with one ("Scale ratio 1.25") is skipped
    because "Scale Ratio" is not capitalised as a pair.
    """
    if not text:
        return frozenset()
    prefix = _BRAND_PREFIX_RE.search(text)
    if not prefix:
        return frozenset()
    body = re.sub(r"\([^)]*\)", " ", text[prefix.end():])
    families = set()
    for clause in re.split(r"(?<!\d)\.(?!\d)|[,;+/]|\band\b|\bplus\b|&", body):
        words = clause.strip()
        m = _FAMILY_RE.match(words)
        if not m:
            continue
        family = m.group(0)
        # A one-word lead followed by a lower-case word that is not a weight is prose, not a face.
        rest = words[m.end():].strip()
        if " " not in family and rest and not re.match(r"\d|for\b|as\b|is\b|at\b|in\b|$", rest):
            continue
        families.add(family.lower())
    return frozenset(families)


def brand_fonts_from_memory(scope: str | None = None) -> frozenset[str]:
    """Brand fonts from the active `design-type` learning (skill impeccable) of `scope`, default this project.

    Never raises: any problem yields an empty set, so the font rule just runs unfiltered.
    """
    try:
        scope = scope or get_scope()
        if scope is None:
            return frozenset()
        hits = [m for m in search(words=[], scopes=[scope], kind="learning", skill="impeccable")
                if m.key == "design-type"]
        return parse_brand_fonts(text=hits[0].text) if hits else frozenset()
    except Exception:  # noqa: BLE001 - a missing brief must never stop a scan
        return frozenset()


# Vendored, generated or tool-owned trees: findings there are not the user's to fix.
_SKIPPED_DIRS = frozenset({"node_modules", "dist", "build"})

_SUPPRESS_HINT = (
    "Fix each finding. To keep a deliberate one, put `/* impeccable-disable-next-line <rule>: <reason> */` "
    "(or `<!-- ... -->` in markup) on the line above it."
)


def _ui_files(root: Path) -> Iterator[Path]:
    """UI source files under `root`, sorted, skipping hidden and vendor directories."""

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in _SKIPPED_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() in UI_EXTENSIONS:
                yield path


def _display(path: Path, base: Path) -> str:
    """`path` relative to `base` when it sits under it, else absolute."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def cmd_design_check(paths: list[str], hook: bool) -> None:
    if hook:
        _run_hook()
        return
    if not paths:
        print("vague design-check: missing PATHS: give one or more files or directories, "
              "or --hook to read a hook payload",
              file=sys.stderr)
        raise typer.Exit(code=2)
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        for p in missing:
            print(f"vague design-check: no such file or directory: {p}", file=sys.stderr)
        raise typer.Exit(code=2)

    brand_fonts = brand_fonts_from_memory()
    count = 0
    for arg in paths:
        root = Path(arg)
        files = _ui_files(root=root) if root.is_dir() else iter([root])
        for path in files:
            for finding in check(path=path, brand_fonts=brand_fonts):
                # normpath drops the leading `./` a `.` argument would add to every line.
                print(f"{os.path.normpath(path)}:{finding.line}: {finding.rule_id}: {finding.message}")
                count += 1
    if count:
        print(f"FAILED: {count} finding(s)")
        raise typer.Exit(code=1)
    print("OK: no findings")


def _run_hook() -> None:
    """PostToolUse hook: findings go to stderr with exit 2, which Claude Code feeds back to Claude.

    Runs after every Edit and Write while /impeccable is loaded, so anything other than a
    finding (no payload, bad JSON, a non-UI file, a crash) exits 0 silently.
    """
    lines: list[str] = []
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return
        path = edited_file(payload=payload)
        if path is None:
            return
        cwd_raw = payload.get("cwd")
        cwd = Path(os.path.realpath(cwd_raw)) if isinstance(cwd_raw, str) and cwd_raw else Path.cwd()

        if path.suffix.lower() not in UI_EXTENSIONS or not path.is_file():
            return
        # The session's project is the payload cwd, not the hook process's own cwd.
        brand_fonts = brand_fonts_from_memory(scope=get_scope(cwd=cwd))
        findings = check(path=path, brand_fonts=brand_fonts)
        if findings:
            shown = _display(path=path, base=cwd)
            lines.append(f"vague design-check: {len(findings)} finding(s) in {shown}")
            lines += [f"{shown}:{f.line}: {f.rule_id}: {f.message}" for f in findings]
            lines.append(_SUPPRESS_HINT)
    except json.JSONDecodeError:
        return
    except Exception as e:
        get_logger().warning("design-check hook failed: %s", e)
        return

    # Exit outside the try block so `except Exception` cannot swallow it.
    if lines:
        print("\n".join(lines), file=sys.stderr)
        raise typer.Exit(code=2)
