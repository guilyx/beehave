"""Draw ``palette/palette.svg``, the swatch sheet, from ``tokens/tokens.json``.

Usage::

    python3.branding / tools / build_palette_svg.py

Standard library only. Text is set in the brand faces with system fallbacks, so
the SVG stays small and its hex codes stay selectable. ``palette/palette.png`` is
a copy rasterised in a browser with Archivo and Martian Mono installed.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_palette import apca_lc, resolve_hex, simulate, wcag_ratio

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens" / "tokens.json"
OUT = ROOT / "palette" / "palette.svg"

SANS = "Archivo, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'Martian Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"
W, H, M = 1600, 1350, 64  # sheet width, height, outer margin
SIMS = ("normal", "protan", "deutan", "tritan")
CAPS = 'letter-spacing="1"'

PIGMENTS = [
    ("pollen", "85", "brand · warning fill"),
    ("pollen", "80", "brand on dark"),
    ("pollen", "52", "ochre line on paper"),
    ("leaf", "50", "success · light"),
    ("leaf", "76", "success · dark"),
    ("cinnabar", "53", "failure · light"),
    ("cinnabar", "70", "failure · dark"),
    ("prussian", "37", "preemption · light"),
    ("prussian", "69", "preemption · dark"),
]

# (label, colour role, dash pattern, stroke width)
EDGES = (
    ("then", "edge", "", 1.75),
    ("ok", "success", "", 1.75),
    ("fail", "failure", "7 4", 1.75),
    ("interrupt", "preempt", "2 4", 2.5),
)


@dataclass(frozen=True)
class Font:
    """How to set one piece of text."""

    fill: str
    size: float = 12
    mono: bool = True
    weight: int = 400
    anchor: str = "start"
    extra: str = ""


@dataclass(frozen=True)
class Box:
    """A rectangle on the sheet."""

    x: float
    y: float
    w: float
    h: float


def esc(s: str) -> str:
    """Escape text for SVG.

    Args:
        s: Raw text.

    Returns:
        Text safe inside an SVG element.
    """
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x: float, y: float, s: str, font: Font) -> str:
    """Return an SVG text element.

    Args:
        x: Anchor x.
        y: Baseline y.
        s: The string.
        font: Fill, size, face, weight, anchor and extra attributes.

    Returns:
        SVG markup.
    """
    fam = MONO if font.mono else SANS
    return (
        f'<text x="{x:g}" y="{y:g}" fill="{font.fill}" font-family="{fam}" '
        f'font-size="{font.size:g}" font-weight="{font.weight}" text-anchor="{font.anchor}" '
        f"{font.extra}>{esc(s)}</text>"
    )


def ink_for(hx: str, light: str, dark: str) -> str:
    """Pick whichever of two text colours contrasts more with a swatch.

    Args:
        hx: Swatch colour.
        light: Light candidate.
        dark: Dark candidate.

    Returns:
        The better text colour.
    """
    return light if wcag_ratio(light, hx) >= wcag_ratio(dark, hx) else dark


def comb_row(doc: dict, y: float, ink: str, paper: str, muted: str) -> list[str]:
    """Draw the neutral ramp as one continuous strip.

    Args:
        doc: Parsed tokens.
        y: Top of the row.
        ink: Dark text colour.
        paper: Light text colour.
        muted: Caption colour.

    Returns:
        SVG elements.
    """
    comb = doc["color"]["palette"]["comb"]
    steps = [(k, v) for k, v in comb.items() if not k.startswith("$")]
    caption = "COMB  ·  WARM NEUTRALS, HUE 80  ·  STEP = OKLCH LIGHTNESS × 100"
    out = [text(M, y, caption, Font(muted, extra=CAPS))]
    sw = (W - 2 * M) / len(steps)
    for i, (step, tok) in enumerate(steps):
        x, hx = M + i * sw, tok["$value"]["hex"]
        out.append(
            f'<rect x="{x:g}" y="{y + 16:g}" width="{sw + 0.5:g}" height="112" fill="{hx}"/>'
        )
        big = Font(ink_for(hx, paper, ink), 22, mono=False, weight=700)
        out.append(text(x + 10, y + 44, step, big))
        out.append(text(x + 10, y + 148, hx, Font(ink)))
        chroma = tok["$value"]["components"][1]
        out.append(text(x + 10, y + 166, f"C {chroma:.3f}", Font(muted, 11)))
    out.append(
        f'<rect x="{M}" y="{y + 16:g}" width="{W - 2 * M}" height="112" fill="none" '
        f'stroke="{muted}" stroke-width="1"/>'
    )
    return out


def pigment_row(doc: dict, y: float, ink: str, paper: str, muted: str) -> list[str]:
    """Draw the accent and status pigments.

    Args:
        doc: Parsed tokens.
        y: Top of the row.
        ink: Dark text colour.
        paper: Light text colour.
        muted: Caption colour.

    Returns:
        SVG elements.
    """
    out = [text(M, y, "POLLEN · LEAF · CINNABAR · PRUSSIAN", Font(muted, extra=CAPS))]
    gap = 6
    sw = (W - 2 * M - gap * (len(PIGMENTS) - 1)) / len(PIGMENTS)
    pal = doc["color"]["palette"]
    for i, (fam, step, role) in enumerate(PIGMENTS):
        tok = pal[fam][step]
        x, hx = M + i * (sw + gap), tok["$value"]["hex"]
        fg = ink_for(hx, paper, ink)
        lum, c, h = tok["$value"]["components"]
        out += [
            f'<rect x="{x:g}" y="{y + 16:g}" width="{sw:g}" height="120" fill="{hx}"/>',
            text(x + 10, y + 42, fam, Font(fg, 16, mono=False, weight=700)),
            text(x + 10, y + 62, step, Font(fg, 14, mono=False)),
            text(x + 10, y + 124, hx, Font(fg)),
            text(x, y + 156, f"oklch({lum:g} {c:g} {h:g})", Font(ink, 11)),
            text(x, y + 174, role, Font(muted, 11)),
        ]
    return out


def markers(doc: dict) -> str:
    """Define a filled arrowhead marker for every edge colour in both themes.

    Args:
        doc: Parsed tokens.

    Returns:
        A defs element.
    """
    out = []
    for theme in ("light", "dark"):
        for _, role, _, _ in EDGES:
            colour = resolve_hex(doc, f"color.{theme}.{role}")
            out.append(
                f'<marker id="m-{theme}-{role}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M0 0L10 5L0 10z" fill="{colour}"/></marker>'
            )
    return "<defs>" + "".join(out) + "</defs>"


def panel_pairs(doc: dict, theme: str, box: Box) -> list[str]:
    """Draw text pairings with their WCAG ratio and APCA Lc.

    Args:
        doc: Parsed tokens.
        theme: ``light`` or ``dark``.
        box: Panel rectangle.

    Returns:
        SVG elements.
    """
    bg = resolve_hex(doc, f"color.{theme}.bg")
    t3 = resolve_hex(doc, f"color.{theme}.text-3")
    samples = (
        ("text", "Now: FlyToWaypoint."),
        ("text-2", "Secondary. Edge labels."),
        ("text-3", "Tertiary. retry ×3"),
        ("success", "ok"),
        ("failure", "fail"),
        ("preempt", "[IsBatteryCritical]"),
    )
    out = []
    for i, (role, label) in enumerate(samples):
        y = box.y + 84 + i * 34
        fg = resolve_hex(doc, f"color.{theme}.{role}")
        weight = 400 if role.startswith("text") else 600
        out.append(text(box.x + 28, y, label, Font(fg, 16, mono=False, weight=weight)))
        ratio, lc = wcag_ratio(fg, bg), apca_lc(fg, bg)
        line = f"{role:<8} {ratio:5.2f}:1  Lc {lc:+.0f}"
        out.append(text(box.x + 262, y, line, Font(t3, 11, extra='xml:space="preserve"')))
    return out


def panel_edges(doc: dict, theme: str, box: Box) -> list[str]:
    """Draw the four edge styles.

    Args:
        doc: Parsed tokens.
        theme: ``light`` or ``dark``.
        box: Panel rectangle.

    Returns:
        SVG elements.
    """
    t2 = resolve_hex(doc, f"color.{theme}.text-2")
    x, out = box.x + box.w - 244, []
    for i, (label, role, dash, width) in enumerate(EDGES):
        y = box.y + 84 + i * 30
        colour = resolve_hex(doc, f"color.{theme}.{role}")
        d = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(
            f'<path d="M{x:g} {y - 4:g}h96" stroke="{colour}" stroke-width="{width:g}"{d} '
            f'fill="none" marker-end="url(#m-{theme}-{role})"/>'
        )
        out.append(text(x + 112, y, label, Font(t2)))
    return out


def panel_nodes(doc: dict, theme: str, box: Box) -> list[str]:
    """Draw one of each node kind.

    Args:
        doc: Parsed tokens.
        theme: ``light`` or ``dark``.
        box: Panel rectangle.

    Returns:
        SVG elements.
    """

    def c(role: str) -> str:
        return resolve_hex(doc, f"color.{theme}.{role}")

    y, x = box.y + box.h - 58, box.x + 28
    t1, on_st = c("text"), c("on-status")
    hexagon = " ".join(
        f"{x + 200 + dx:g},{y + dy:g}"
        for dx, dy in ((0, 0), (14, -18), (110, -18), (124, 0), (110, 18), (14, 18))
    )
    octagon = " ".join(
        f"{x + 588 + dx * 28:g},{y + dy * 28:g}"
        for dx, dy in (
            (-0.414, -1), (0.414, -1), (1, -0.414), (1, 0.414),
            (0.414, 1), (-0.414, 1), (-1, 0.414), (-1, -0.414),
        )
    )  # fmt: skip
    small = Font(on_st, 9, mono=False, weight=700, anchor="middle")
    return [
        f'<circle cx="{x + 26:g}" cy="{y:g}" r="26" fill="{c("inverse")}"/>',
        text(x + 26, y + 4, "START", Font(c("on-inverse"), 10, False, 700, "middle")),
        (
            f'<rect x="{x + 72:g}" y="{y - 18:g}" width="112" height="36" '
            f'fill="{c("surface")}" stroke="{t1}" stroke-width="1.5"/>'
        ),
        text(x + 128, y + 5, "Action", Font(t1, 14, False, 600, "middle")),
        f'<polygon points="{hexagon}" fill="{c("sunken")}" stroke="{t1}" stroke-width="1.5"/>',
        text(x + 262, y + 4, "[Guard]", Font(t1, 12, anchor="middle")),
        (
            f'<rect x="{x + 340:g}" y="{y - 18:g}" width="132" height="36" '
            f'fill="{c("warn-fill")}" stroke="{c("warn-line")}" stroke-width="1.5" '
            f'stroke-dasharray="4 3"/>'
        ),
        text(x + 406, y + 4, "~ approximated", Font(c("on-accent"), 11, anchor="middle")),
        f'<circle cx="{x + 516:g}" cy="{y:g}" r="28" fill="{c("success")}"/>',
        (
            f'<circle cx="{x + 516:g}" cy="{y:g}" r="24" fill="none" stroke="{on_st}" '
            f'stroke-width="1.5"/>'
        ),
        text(x + 516, y + 4, "SUCCESS", small),
        f'<polygon points="{octagon}" fill="{c("failure")}"/>',
        text(x + 588, y + 4, "FAILURE", small),
    ]


def theme_panel(doc: dict, theme: str, box: Box) -> list[str]:
    """Draw one theme panel.

    Args:
        doc: Parsed tokens.
        theme: ``light`` or ``dark``.
        box: Panel rectangle.

    Returns:
        SVG elements.
    """
    bg, rule = resolve_hex(doc, f"color.{theme}.bg"), resolve_hex(doc, f"color.{theme}.rule")
    t2 = resolve_hex(doc, f"color.{theme}.text-2")
    return [
        (
            f'<rect x="{box.x:g}" y="{box.y:g}" width="{box.w:g}" height="{box.h:g}" '
            f'fill="{bg}" stroke="{rule}"/>'
        ),
        text(box.x + 28, box.y + 40, f"{theme.upper()} THEME", Font(t2, extra=CAPS)),
        *panel_pairs(doc, theme, box),
        *panel_edges(doc, theme, box),
        *panel_nodes(doc, theme, box),
    ]


def cvd_cell(doc: dict, theme: str, sim: str, box: Box) -> list[str]:
    """Draw the graph colours of one theme under one simulation.

    Args:
        doc: Parsed tokens.
        theme: ``light`` or ``dark``.
        sim: Simulation name.
        box: Cell rectangle.

    Returns:
        SVG elements.
    """

    def c(role: str) -> str:
        return simulate(resolve_hex(doc, f"color.{theme}.{role}"), sim)

    out = [
        (
            f'<rect x="{box.x:g}" y="{box.y:g}" width="{box.w:g}" height="{box.h:g}" '
            f'fill="{c("bg")}"/>'
        ),
        text(box.x + 20, box.y + 24, f"{theme} · {sim}", Font(c("text-2"), 11)),
    ]
    for j, (_, role, dash, width) in enumerate(EDGES):
        y = box.y + 46 + j * 18
        d = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(
            f'<path d="M{box.x + 20:g} {y:g}h150" stroke="{c(role)}" stroke-width="{width:g}"{d}/>'
        )
    for k, role in enumerate(("inverse", "success", "failure", "warn-fill")):
        out.append(
            f'<rect x="{box.x + 200 + k * 36:g}" y="{box.y + 44:g}" width="28" height="56" '
            f'fill="{c(role)}"/>'
        )
    return out


def cvd_strip(doc: dict, y: float, ink: str, muted: str) -> list[str]:
    """Show the graph colours under every colour-vision simulation, both themes.

    Args:
        doc: Parsed tokens.
        y: Top of the strip.
        ink: Caption colour.
        muted: Secondary caption colour.

    Returns:
        SVG elements.
    """
    caption = (
        "COLOUR-VISION CHECK  ·  MACHADO ET AL. 2009, SEVERITY 1.0  ·  "
        "LINE STYLE CARRIES THE MEANING EVEN WITHOUT COLOUR"
    )
    out = [text(M, y, caption, Font(muted, extra=CAPS))]
    col_w = (W - 2 * M) / 4
    for row, theme in enumerate(("light", "dark")):
        for i, sim in enumerate(SIMS):
            inset = 4 if i else 0
            box = Box(M + i * col_w + inset, y + 24 + row * 132, col_w - 4, 120)
            out += cvd_cell(doc, theme, sim, box)
    note = (
        "Lines: then · ok · fail · interrupt. Blocks: START · SUCCESS · FAILURE · warning. "
        "Checked by tools/check_palette.py."
    )
    out.append(text(M, y + 300, note, Font(ink, 11)))
    return out


def header(doc: dict) -> list[str]:
    """Draw the sheet title.

    Args:
        doc: Parsed tokens.

    Returns:
        SVG elements.
    """

    def c(role: str) -> str:
        return resolve_hex(doc, f"color.light.{role}")

    title = Font(c("text"), 22, mono=False, weight=800, extra='style="font-stretch:125%"')
    right = Font(c("text-2"), anchor="end", extra=CAPS)
    return [
        f'<rect x="{M}" y="{M - 8}" width="40" height="40" fill="{c("accent")}"/>',
        text(M + 56, M + 10, "BEEHAVE  ·  PLATE 2", Font(c("text-2"), extra=CAPS)),
        text(M + 56, M + 32, "Palette", title),
        text(W - M, M + 10, "OKLCH · WCAG 2.2 · APCA 0.0.98G · CVD-CHECKED", right),
    ]


def build(doc: dict) -> str:
    """Compose the whole sheet.

    Args:
        doc: Parsed tokens.

    Returns:
        SVG document text.
    """
    paper = resolve_hex(doc, "color.light.bg")
    ink = resolve_hex(doc, "color.light.text")
    muted = resolve_hex(doc, "color.light.text-2")
    pw = (W - 2 * M - 16) / 2
    body = [
        markers(doc),
        f'<rect width="{W}" height="{H}" fill="{paper}"/>',
        *header(doc),
        *comb_row(doc, 150, ink, paper, muted),
        *pigment_row(doc, 380, ink, paper, muted),
        *theme_panel(doc, "light", Box(M, 600, pw, 360)),
        *theme_panel(doc, "dark", Box(M + pw + 16, 600, pw, 360)),
        *cvd_strip(doc, 1010, ink, muted),
    ]
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="Beehave palette">\n<title>Beehave palette</title>\n'
    )
    return head + "\n".join(body) + "\n</svg>\n"


def main() -> int:
    """Write palette/palette.svg.

    Returns:
        Process exit code.
    """
    doc = json.loads(TOKENS.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(doc), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
