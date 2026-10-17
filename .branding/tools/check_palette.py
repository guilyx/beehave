"""Check the Beehave palette: WCAG 2.2 contrast, APCA and colour-vision deficiency.

Reads ``tokens/tokens.json`` (W3C Design Tokens format) and reports:

1. Every primitive: OKLCH to sRGB hex round trip, and sRGB gamut.
2. The WCAG 2.2 contrast ratio and APCA Lc of every recommended pairing, in the
   light and the dark theme. WCAG is the gate; APCA is reported against its
   published targets because it is still a draft.
3. Protanopia, deuteranopia and tritanopia simulation (Machado, Oliveira and
   Fernandes 2009, severity 1.0) of the graph colours: the smallest OKLab distance
   between any two of them, and each edge colour's contrast with the background
   after simulation.

Standard library only (Python 3.10+). Run from anywhere::

    python3.branding / tools / check_palette.py  # text report, exit 1 on failure
    python3.branding / tools / check_palette.py - -markdown  # Markdown tables
    python3.branding / tools / check_palette.py - -fix - hex  # rewrite hex fallbacks from OKLCH
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

TOKENS = Path(__file__).resolve().parent.parent / "tokens" / "tokens.json"

# ---------------------------------------------------------------------------
# Colour maths
# ---------------------------------------------------------------------------


def srgb_decode(c: float) -> float:
    """Convert an sRGB channel (0-1) to linear light, as WCAG 2.2 defines it.

    Args:
        c: Encoded channel value.

    Returns:
        Linear channel value.
    """
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def srgb_encode(x: float) -> float:
    """Convert a linear channel to sRGB encoding, clipping to 0-1.

    Args:
        x: Linear channel value.

    Returns:
        Encoded channel value.
    """
    x = min(max(x, 0.0), 1.0)
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def oklab_to_linear(L: float, a: float, b: float) -> tuple[float, float, float]:
    """Convert OKLab to linear sRGB (Ottosson 2020).

    Args:
        L: Lightness, 0-1.
        a: Green-red axis.
        b: Blue-yellow axis.

    Returns:
        Linear sRGB triple (may fall outside 0-1 when out of gamut).
    """
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_**3, m_**3, s_**3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def linear_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert linear sRGB to OKLab (Ottosson 2020).

    Args:
        r: Linear red.
        g: Linear green.
        b: Linear blue.

    Returns:
        OKLab triple.
    """
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def rgb_to_hex(rgb) -> str:
    """Format encoded channels (0-1) as ``#rrggbb``.

    Args:
        rgb: Iterable of three encoded channel values.

    Returns:
        Hex colour.
    """
    return "#" + "".join(f"{round(min(max(c, 0), 1) * 255):02x}" for c in rgb)


def hex_to_rgb(hx: str) -> tuple[float, float, float]:
    """Parse ``#rrggbb`` into encoded channels, 0-1.

    Args:
        hx: Hex colour.

    Returns:
        Encoded RGB triple.
    """
    hx = hx.lstrip("#")
    return (int(hx[0:2], 16) / 255, int(hx[2:4], 16) / 255, int(hx[4:6], 16) / 255)


def oklch_to_hex(L: float, C: float, h: float) -> tuple[str, bool]:
    """Convert OKLCH to an sRGB hex string.

    Args:
        L: Lightness, 0-1.
        C: Chroma.
        h: Hue in degrees.

    Returns:
        The hex string and whether the colour is inside the sRGB gamut.
    """
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    lin = oklab_to_linear(L, a, b)
    in_gamut = all(-1e-4 <= v <= 1 + 1e-4 for v in lin)
    return rgb_to_hex(srgb_encode(v) for v in lin), in_gamut


def delta_e_ok(h1: str, h2: str) -> float:
    """Return the Euclidean OKLab distance between two colours.

    About 0.02 is one just-noticeable step; the palette asks for 0.08 between
    graph colours.

    Args:
        h1: First hex colour.
        h2: Second hex colour.

    Returns:
        Distance in OKLab units.
    """
    a = linear_to_oklab(*(srgb_decode(c) for c in hex_to_rgb(h1)))
    b = linear_to_oklab(*(srgb_decode(c) for c in hex_to_rgb(h2)))
    return math.dist(a, b)


def relative_luminance(hx: str) -> float:
    """Return WCAG 2.2 relative luminance.

    Args:
        hx: Hex colour.

    Returns:
        Luminance, 0-1.
    """
    r, g, b = (srgb_decode(c) for c in hex_to_rgb(hx))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_ratio(fg: str, bg: str) -> float:
    """Return the WCAG 2.2 contrast ratio of two colours.

    Args:
        fg: Foreground hex.
        bg: Background hex.

    Returns:
        Ratio from 1 to 21.
    """
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def apca_y(hx: str) -> float:
    """Return APCA screen luminance Y (0.0.98G-4g constants).

    Args:
        hx: Hex colour.

    Returns:
        Luminance estimate.
    """
    r, g, b = hex_to_rgb(hx)
    return 0.2126729 * r**2.4 + 0.7151522 * g**2.4 + 0.0721750 * b**2.4


def apca_lc(fg: str, bg: str) -> float:
    """Return APCA lightness contrast Lc (0.0.98G-4g, github.com/Myndex/apca-w3).

    Positive for dark text on a light background, negative for the reverse.

    Args:
        fg: Text hex.
        bg: Background hex.

    Returns:
        Lc, roughly -108 to 106.
    """
    blk_thrs, blk_clmp = 0.022, 1.414
    txt, back = apca_y(fg), apca_y(bg)
    txt = txt if txt > blk_thrs else txt + (blk_thrs - txt) ** blk_clmp
    back = back if back > blk_thrs else back + (blk_thrs - back) ** blk_clmp
    if abs(back - txt) < 0.0005:
        return 0.0
    if back > txt:
        sapc = (back**0.56 - txt**0.57) * 1.14
        out = 0.0 if sapc < 0.1 else sapc - 0.027
    else:
        sapc = (back**0.65 - txt**0.62) * 1.14
        out = 0.0 if sapc > -0.1 else sapc + 0.027
    return out * 100


# Machado, Oliveira & Fernandes (2009), severity 1.0, applied to linear RGB.
MACHADO = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritan": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}
SIMS = ("normal", "protan", "deutan", "tritan")


def simulate(hx: str, kind: str) -> str:
    """Simulate how a colour looks with a colour-vision deficiency.

    Args:
        hx: Hex colour.
        kind: One of ``normal``, ``protan``, ``deutan``, ``tritan``.

    Returns:
        The simulated hex colour.
    """
    if kind == "normal":
        return hx
    lin = [srgb_decode(c) for c in hex_to_rgb(hx)]
    rows = MACHADO[kind]
    return rgb_to_hex(
        srgb_encode(sum(m * v for m, v in zip(row, lin, strict=True))) for row in rows
    )


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def get(doc: dict, dotted: str) -> dict:
    """Look up a token or group by dotted path.

    Args:
        doc: Parsed tokens.
        dotted: Path such as ``color.light.bg``.

    Returns:
        The token object.
    """
    node = doc
    for part in dotted.split("."):
        node = node[part]
    return node


def resolve_hex(doc: dict, dotted: str) -> str:
    """Resolve a colour token, following aliases, to its hex value.

    Args:
        doc: Parsed tokens.
        dotted: Path such as ``color.dark.text``.

    Returns:
        Hex colour.
    """
    value = get(doc, dotted)["$value"]
    while isinstance(value, str) and value.startswith("{"):
        value = get(doc, value.strip("{}"))["$value"]
    return value["hex"]


def primitives(doc: dict):
    """Yield every primitive colour as (family, step, token).

    Args:
        doc: Parsed tokens.

    Yields:
        Tuples of family name, step name and token object.
    """
    for fam, steps in doc["color"]["palette"].items():
        if fam.startswith("$"):
            continue
        for step, tok in steps.items():
            if not step.startswith("$"):
                yield fam, step, tok


# ---------------------------------------------------------------------------
# What the palette promises
# ---------------------------------------------------------------------------

# kind -> (WCAG 2.2 minimum, APCA Lc target)
#   body   running text, 16px regular
#   text   secondary text, 14px and up
#   label  short bold labels: status words, terminal nodes, 12px notes
#   ui     non-text: node borders, edges, focus rings
KIND = {"body": (4.5, 75), "text": (4.5, 60), "label": (4.5, 45), "ui": (3.0, 30)}

# (foreground role, background role, kind[, only this theme])
PAIRS = [
    ("text", "bg", "body"),
    ("text", "surface", "body"),
    ("text", "sunken", "body"),
    ("text-2", "bg", "text"),
    ("text-2", "surface", "text"),
    ("text-2", "sunken", "text"),
    ("text-3", "bg", "label"),
    ("text-3", "surface", "label"),
    ("on-inverse", "inverse", "body"),
    ("on-accent", "accent", "text"),
    ("warn-line", "warn-fill", "text"),
    ("accent-line", "bg", "label"),
    ("success", "bg", "label"),
    ("success", "surface", "label"),
    ("failure", "bg", "label"),
    ("failure", "surface", "label"),
    ("preempt", "bg", "label"),
    ("preempt", "surface", "label"),
    ("on-status", "success", "label"),
    ("on-status", "failure", "label"),
    ("on-status", "preempt", "label"),
    ("text", "surface", "ui"),  # node border on node fill
    ("border", "bg", "ui"),
    ("border", "surface", "ui"),
    ("edge", "bg", "ui"),
    ("warn-line", "bg", "ui", "light"),  # light: the dashed ink border outlines the block
    ("warn-fill", "bg", "ui", "dark"),  # dark: the pollen fill itself outlines the block
    ("focus", "bg", "ui"),
]

# Colours that must stay apart from each other in a rendered graph.
CVD_SETS = {
    "edges": ["success", "failure", "preempt", "edge"],  # lines
    "fills": ["inverse", "success", "failure", "warn-fill"],  # START, SUCCESS, FAILURE, warning
}
CVD_MIN_DE = 0.08  # OKLab distance, about four just-noticeable steps


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


class Report:
    """Collects tables and failures, then prints them as text or Markdown."""

    def __init__(self, markdown: bool) -> None:
        self.markdown = markdown
        self.lines: list[str] = []
        self.failures: list[str] = []

    def heading(self, title: str) -> None:
        """Add a section heading.

        Args:
            title: Heading text.
        """
        self.lines += [f"### {title}" if self.markdown else f"== {title}", ""]

    def table(self, headers: list[str], rows: list[tuple]) -> None:
        """Add a table.

        Args:
            headers: Column titles.
            rows: Row tuples.
        """
        cells = [[str(c) for c in r] for r in rows]
        if self.markdown:
            self.lines.append("| " + " | ".join(headers) + " |")
            self.lines.append("|" + "|".join("---" for _ in headers) + "|")
            self.lines += ["| " + " | ".join(r) + " |" for r in cells]
        else:
            widths = [max(len(x) for x in col) for col in zip(headers, *cells, strict=True)]
            self.lines.append("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)))
            self.lines.append("  ".join("-" * w for w in widths))
            for r in cells:
                self.lines.append("  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)))
        self.lines.append("")

    def fail(self, message: str) -> None:
        """Record a failed check.

        Args:
            message: What failed.
        """
        self.failures.append(message)


def check_primitives(doc: dict, rep: Report, fix_hex: bool) -> None:
    """Check each primitive's hex fallback and gamut.

    Args:
        doc: Parsed tokens (hex values are rewritten in place with ``fix_hex``).
        rep: Report to add to.
        fix_hex: Rewrite stale hex fallbacks.
    """
    rep.heading("Primitives (OKLCH to sRGB)")
    rows = []
    for fam, step, tok in primitives(doc):
        L, C, h = tok["$value"]["components"]
        hx, in_gamut = oklch_to_hex(L, C, h)
        if fix_hex:
            tok["$value"]["hex"] = hx
        stored = tok["$value"].get("hex", "")
        status = "ok"
        if not in_gamut:
            status = "OUT OF GAMUT"
        elif stored != hx:
            status = "HEX MISMATCH (run --fix-hex)"
        if status != "ok":
            rep.fail(f"{fam}-{step}: {status}")
        rows.append((f"{fam}-{step}", f"oklch({L:.3f} {C:.3f} {h:g})", stored, status))
    rep.table(["token", "oklch", "hex", "check"], rows)


def check_contrast(doc: dict, rep: Report, theme: str) -> None:
    """Check every recommended pairing in one theme.

    Args:
        doc: Parsed tokens.
        rep: Report to add to.
        theme: ``light`` or ``dark``.
    """
    rep.heading(f"Contrast, {theme} theme")
    rows = []
    for fg, bg, kind, *only in PAIRS:
        if only and only[0] != theme:
            continue
        f = resolve_hex(doc, f"color.{theme}.{fg}")
        b = resolve_hex(doc, f"color.{theme}.{bg}")
        ratio, lc = wcag_ratio(f, b), apca_lc(f, b)
        need, lc_need = KIND[kind]
        if ratio < need:
            rep.fail(f"{theme}: {fg} on {bg} = {ratio:.2f}:1, needs {need}:1")
        apca = "ok" if abs(lc) >= lc_need else f"below {lc_need}"
        verdict = "pass" if ratio >= need else "FAIL"
        rows.append((fg, bg, f, b, kind, f"{ratio:.2f}:1", verdict, f"{lc:+.1f}", apca))
    headers = ["foreground", "background", "fg", "bg", "use", "WCAG", "verdict", "APCA Lc", "APCA"]
    rep.table(headers, rows)


def check_cvd(doc: dict, rep: Report, theme: str) -> None:
    """Simulate colour-vision deficiencies for the graph colours of one theme.

    Args:
        doc: Parsed tokens.
        rep: Report to add to.
        theme: ``light`` or ``dark``.
    """
    rep.heading(f"Colour-vision simulation, {theme} theme (Machado 2009, severity 1.0)")
    bg = resolve_hex(doc, f"color.{theme}.bg")
    rows = []
    for role in CVD_SETS["edges"]:
        hx = resolve_hex(doc, f"color.{theme}.{role}")
        cells = [role]
        for sim in SIMS:
            shown = simulate(hx, sim)
            ratio = wcag_ratio(shown, simulate(bg, sim))
            cells.append(f"{shown} {ratio:.1f}:1")
            if ratio < 3.0:
                rep.fail(f"{theme}/{sim}: edge '{role}' only {ratio:.2f}:1 on bg")
        rows.append(tuple(cells))
    rep.table(["edge colour", *(f"{s} (hex, vs bg)" for s in SIMS)], rows)

    rows = []
    for set_name, roles in CVD_SETS.items():
        hexes = {r: resolve_hex(doc, f"color.{theme}.{r}") for r in roles}
        cells = [set_name]
        for sim in SIMS:
            d, a, b = min(
                (delta_e_ok(simulate(hexes[a], sim), simulate(hexes[b], sim)), a, b)
                for a, b in itertools.combinations(roles, 2)
            )
            if d < CVD_MIN_DE:
                rep.fail(f"{theme}/{sim}: {a} vs {b} ΔEok {d:.3f} < {CVD_MIN_DE}")
            cells.append(f"{d:.3f} ({a}/{b})" + ("" if d >= CVD_MIN_DE else " LOW"))
        rows.append(tuple(cells))
    rep.table(["set", *(f"min ΔEok {s}" for s in SIMS)], rows)


def run(doc: dict, markdown: bool = False, fix_hex: bool = False) -> list[str]:
    """Run every check and print the report.

    Args:
        doc: Parsed tokens.
        markdown: Print Markdown tables.
        fix_hex: Rewrite stale hex fallbacks in ``doc``.

    Returns:
        The list of failures (empty when everything passes).
    """
    rep = Report(markdown)
    check_primitives(doc, rep, fix_hex)
    for theme in ("light", "dark"):
        check_contrast(doc, rep, theme)
    for theme in ("light", "dark"):
        check_cvd(doc, rep, theme)
    rep.heading("Result")
    if rep.failures:
        rep.lines += [f"FAIL  {f}" for f in rep.failures]
    else:
        rep.lines.append(
            "All recommended pairs pass WCAG 2.2 AA. Every graph colour stays at least "
            f"{CVD_MIN_DE} ΔEok from the others and at least 3:1 against the background "
            "under every simulation."
        )
    print("\n".join(rep.lines))
    return rep.failures


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments (defaults to ``sys.argv``).

    Returns:
        0 when every check passes, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description="Check the Beehave palette.")
    parser.add_argument("--tokens", type=Path, default=TOKENS, help="path to tokens.json")
    parser.add_argument("--markdown", action="store_true", help="print Markdown tables")
    parser.add_argument("--fix-hex", action="store_true", help="rewrite hex fallbacks from OKLCH")
    args = parser.parse_args(argv)
    doc = json.loads(args.tokens.read_text(encoding="utf-8"))
    failures = run(doc, markdown=args.markdown, fix_hex=args.fix_hex)
    if args.fix_hex:
        text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        args.tokens.write_text(text, encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
