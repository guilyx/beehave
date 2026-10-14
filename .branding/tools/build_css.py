"""Build ``tokens/tokens.css`` from ``tokens/tokens.json``.

Usage::

    python3.branding / tools / build_css.py  # write tokens/tokens.css
    python3.branding / tools / build_css.py - -check  # exit 1 if tokens.css is stale

Standard library only. Colours are written as sRGB hex (every Beehave colour sits
inside sRGB, so the hex is exact) with the OKLCH source in a comment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens" / "tokens.json"
CSS = ROOT / "tokens" / "tokens.css"
GENERIC = {"serif", "sans-serif", "monospace", "system-ui", "ui-monospace"}


def items(group: dict) -> list[tuple[str, dict]]:
    """Return a group's children, skipping ``$`` properties.

    Args:
        group: A token group.

    Returns:
        (name, token) pairs.
    """
    return [(k, v) for k, v in group.items() if not k.startswith("$")]


def var_name(ref: str) -> str:
    """Turn an alias into the CSS custom property it maps to (without ``--bh-``).

    Args:
        ref: Alias such as ``{color.palette.comb.96}`` or ``{font.weight.bold}``.

    Returns:
        Name such as ``comb-96`` or ``weight-bold``.
    """
    parts = ref.strip("{}").split(".")
    prefixes = {
        ("color", "palette"): "",
        ("font", "family"): "font-",
        ("font", "weight"): "weight-",
    }
    prefix = prefixes.get((parts[0], parts[1]))
    if prefix is None:
        return "-".join(parts)
    return prefix + "-".join(parts[2:])


def dim(v: dict) -> str:
    """Format a DTCG dimension.

    Args:
        v: ``{"value": n, "unit": "px"}``.

    Returns:
        CSS length such as ``12px`` or ``0``.
    """
    n = v["value"]
    if not n:
        return "0"
    n = int(n) if float(n).is_integer() else n
    return f"{n}{v['unit']}"


def family(names: list[str]) -> str:
    """Format a font stack, quoting family names.

    Args:
        names: Family names, most preferred first.

    Returns:
        CSS font-family value.
    """
    return ", ".join(n if n in GENERIC else f'"{n}"' for n in names)


def colour_block(doc: dict) -> list[str]:
    """Emit primitives and the light theme.

    Args:
        doc: Parsed tokens.

    Returns:
        CSS lines.
    """
    out = ["  /* Primitives: step number = OKLCH lightness x 100 */"]
    for fam, steps in items(doc["color"]["palette"]):
        for step, tok in items(steps):
            lum, c, h = tok["$value"]["components"]
            out.append(f"  --bh-{fam}-{step}: {tok['$value']['hex']}; /* oklch({lum} {c} {h}) */")
    out += ["", "  /* Light theme (default) */"]
    out += theme_lines(doc, "light", "  ")
    return out


def theme_lines(doc: dict, theme: str, indent: str) -> list[str]:
    """Emit the semantic role variables for one theme.

    Args:
        doc: Parsed tokens.
        theme: ``light`` or ``dark``.
        indent: Leading whitespace.

    Returns:
        CSS lines.
    """
    return [
        f"{indent}--bh-{role}: var(--bh-{var_name(tok['$value'])});"
        for role, tok in items(doc["color"][theme])
    ]


def type_block(doc: dict) -> list[str]:
    """Emit font stacks, weights, widths and the type scale.

    Args:
        doc: Parsed tokens.

    Returns:
        CSS lines.
    """
    out = ["  /* Type. --bh-text-* fit the font shorthand. */"]
    out += [f"  --bh-font-{n}: {family(t['$value'])};" for n, t in items(doc["font"]["family"])]
    out += [f"  --bh-weight-{n}: {t['$value']};" for n, t in items(doc["font"]["weight"])]
    out += [f"  --bh-width-{n}: {t['$value']}%;" for n, t in items(doc["font"]["width"])]
    for name, tok in items(doc["typography"]):
        v = tok["$value"]
        weight = f"var(--bh-{var_name(v['fontWeight'])})"
        fam = f"var(--bh-{var_name(v['fontFamily'])})"
        out.append(f"  --bh-text-{name}: {weight} {dim(v['fontSize'])}/{v['lineHeight']} {fam};")
        if v["letterSpacing"]["value"]:
            out.append(f"  --bh-tracking-{name}: {dim(v['letterSpacing'])};")
    return out


def shape_block(doc: dict) -> list[str]:
    """Emit spacing, radii, stroke widths and dash patterns.

    Args:
        doc: Parsed tokens.

    Returns:
        CSS lines.
    """
    out = ["  /* Space (4px grid), radius, stroke */"]
    out += [f"  --bh-space-{n}: {dim(t['$value'])};" for n, t in items(doc["space"])]
    out += [f"  --bh-radius-{n}: {dim(t['$value'])};" for n, t in items(doc["radius"])]
    out += [f"  --bh-stroke-{n}: {dim(t['$value'])};" for n, t in items(doc["stroke"]["width"])]
    for name, tok in items(doc["stroke"]["style"]):
        v = tok["$value"]
        if isinstance(v, dict):
            dashes = " ".join(dim(d).removesuffix("px") for d in v["dashArray"])
            out.append(f"  --bh-dash-{name}: {dashes};")
            out.append(f"  --bh-linecap-{name}: {v['lineCap']};")
        else:
            out.append(f"  --bh-dash-{name}: none;")
    return out


def build(doc: dict) -> str:
    """Render the whole stylesheet.

    Args:
        doc: Parsed tokens.

    Returns:
        CSS text.
    """
    dark = theme_lines(doc, "dark", "    ")
    css = [
        "/* Beehave design tokens. Built from tokens.json with tools/build_css.py;",
        "   edit the JSON, not this file. */",
        "",
        ":root {",
        "  color-scheme: light dark;",
        "",
        *colour_block(doc),
        "",
        *type_block(doc),
        "",
        *shape_block(doc),
        "}",
        "",
        '/* Dark theme follows the system unless the page pins data-theme="light". */',
        "@media (prefers-color-scheme: dark) {",
        '  :root:not([data-theme="light"]) {',
        "    color-scheme: dark;",
        *dark,
        "  }",
        "}",
        "",
        '/* Explicit dark theme, e.g. <html data-theme="dark"> on a field display. */',
        '[data-theme="dark"] {',
        "  color-scheme: dark;",
        *(line[2:] for line in dark),
        "}",
        "",
        '[data-theme="light"] {',
        "  color-scheme: light;",
        "}",
    ]
    return "\n".join(css) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments (defaults to ``sys.argv``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Build tokens.css from tokens.json.")
    parser.add_argument("--check", action="store_true", help="fail if tokens.css is stale")
    args = parser.parse_args(argv)
    css = build(json.loads(TOKENS.read_text(encoding="utf-8")))
    if args.check:
        stale = CSS.read_text(encoding="utf-8") != css
        print("tokens.css is out of date" if stale else "tokens.css is up to date")
        return 1 if stale else 0
    CSS.write_text(css, encoding="utf-8")
    print(f"wrote {CSS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
