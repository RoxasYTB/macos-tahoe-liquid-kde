"""Edition-specific client fills; compositor gradients remain material-owned."""

import gzip
from pathlib import Path
import xml.etree.ElementTree as ET

from theme_switch import default_wallpaper

PLASMA_SURFACES = (
    "dialogs/background.svgz", "dialogs/launcher-search.svgz",
    "widgets/background.svgz", "widgets/translucentbackground.svgz",
    "widgets/tooltip.svgz", "solid/dialogs/background.svgz",
    "solid/widgets/panel-background.svgz", "solid/widgets/tooltip.svgz",
)
_TILES = ("center", "top", "bottom", "left", "right",
          "topleft", "topright", "bottomleft", "bottomright")
_SVG = "http://www.w3.org/2000/svg"
_XLINK = "http://www.w3.org/1999/xlink"


def surface_nodes(root: ET.Element, ids: tuple[str, ...]):
    """Follow tile references without touching masks, shadows or fallbacks."""
    indexed = {node.get("id"): node for node in root.iter() if node.get("id")}
    seen = set()

    def visit(node):
        if node in seen:
            return
        seen.add(node)
        yield node
        reference = node.get(f"{{{_XLINK}}}href", node.get("href", ""))
        if reference.startswith("#") and reference[1:] in indexed:
            yield from visit(indexed[reference[1:]])
        for child in node:
            yield from visit(child)

    for id_ in ids:
        if id_ in indexed:
            yield from visit(indexed[id_])


def set_surface_fill(root: ET.Element, ids: tuple[str, ...], opacity: str,
                     color: str | None = None) -> None:
    for node in surface_nodes(root, ids):
        style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
        fill = style.get("fill", node.get("fill"))
        alpha = style.get("opacity", node.get("opacity", "1"))
        translucent_fill = fill in ("#000000", "#ffffff") and float(alpha) in (.48, .55)
        solid_fallback = fill in ("#333333", "#242424") and float(alpha) == 1.0
        if not (translucent_fill or solid_fallback):
            continue
        if "opacity" in style:
            style["opacity"] = opacity
        else:
            node.set("opacity", opacity)
        if color:
            if "fill" in style:
                style["fill"] = color
            else:
                node.set("fill", color)
        if style:
            node.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))


def clear_menu_client_fill(root: ET.Element) -> None:
    """Remove heavy dark menu fills while retaining rim highlights and shadows."""
    menu_tiles = tuple(node.get("id") for node in root.iter()
                       if node.get("id", "").startswith(("menu-normal", "menu-shadow")))
    for node in surface_nodes(root, menu_tiles):
        style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
        fill = style.get("fill", node.get("fill"))
        alpha = float(style.get("opacity", node.get("opacity", "1")))
        if fill not in ("#000000", "#333333", "#242424") or alpha not in (0.0, 0.12, 0.48, 0.55, 1.0):
            continue
        if "opacity" in style:
            style["opacity"] = "0.0"
        else:
            node.set("opacity", "0.0")
        if style:
            node.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))
    soften_dark_surface_rim(root, menu_tiles)


def soften_dark_surface_rim(root: ET.Element, ids: tuple[str, ...]) -> None:
    for node in surface_nodes(root, ids):
        style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
        fill = style.get("fill", node.get("fill"))
        alpha = float(style.get("opacity", node.get("opacity", "1")))
        if fill != "#000000" or alpha not in (0.06, 0.18):
            continue
        if "opacity" in style:
            style["opacity"] = "0.015"
        else:
            node.set("opacity", "0.015")
        if style:
            node.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))


def soften_menu_frame(root: ET.Element) -> None:
    """Keep the menu's glass edge, but remove its heavy dark outline."""
    menu_tiles = tuple(node.get("id") for node in root.iter()
                       if node.get("id", "").startswith(("menu-normal", "menu-shadow")))
    for node in surface_nodes(root, menu_tiles):
        style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
        fill = style.get("fill", node.get("fill"))
        alpha = float(style.get("opacity", node.get("opacity", "1")))
        dark_shadow = node.get("id") in ("path3", "path22") and fill in (
            "url(#linearGradient3)", "url(#radialGradient5)") and alpha in (0.035, 0.12, 0.5)
        if dark_shadow:
            value = "0.0"
        elif fill == "#000000" and alpha == 0.06:
            value = "0.015"
        elif fill == "#ffffff" and alpha == 0.22:
            value = "0.14"
        else:
            continue
        if "opacity" in style:
            style["opacity"] = value
        else:
            node.set("opacity", value)
        if style:
            node.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))


def _write_svg(path: Path, root: ET.Element) -> None:
    ET.register_namespace("", _SVG)
    ET.register_namespace("xlink", _XLINK)
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    path.write_bytes(gzip.compress(data, mtime=0) if path.suffix == ".svgz" else data)


def apply_plasma_surface_defaults(theme: Path) -> None:
    """Apply to a staged copy of the bundled theme, never user configuration."""
    wallpaper = default_wallpaper()
    is_dark = theme.name.endswith("-Dark")
    if wallpaper == "MacTahoe" and is_dark:
        opacity = "0.0"
        color = None
    elif wallpaper == "MacGoldenGate":
        opacity = "0.60" if not is_dark else "0.01"
        color = "#ffffff"
    else:
        return
    for name in PLASMA_SURFACES:
        path = theme / name
        root = ET.fromstring(gzip.decompress(path.read_bytes()))
        set_surface_fill(root, _TILES, opacity, color)
        if wallpaper == "MacTahoe" and is_dark and name == "widgets/background.svgz":
            soften_dark_surface_rim(root, _TILES)
        if wallpaper == "MacGoldenGate" and name == "dialogs/background.svgz" and not any(
                node.get("id") == "hint-clear-surface" for node in root):
            ET.SubElement(root, f"{{{_SVG}}}rect", {
                "id": "hint-clear-surface", "width": "1", "height": "1", "opacity": "0",
            })
        _write_svg(path, root)


def apply_kvantum_surface_defaults(path: Path) -> None:
    wallpaper = default_wallpaper()
    is_dark = path.stem.endswith("Dark")
    if wallpaper == "MacTahoe" and is_dark:
        opacity = "0.0"
        color = None
    elif wallpaper == "MacGoldenGate":
        opacity = "0.60" if not is_dark else "0.01"
        color = "#ffffff"
    else:
        return
    root = ET.parse(path).getroot()
    # The shadow frame also references the menu's surface tiles.
    ids = tuple(node.get("id") for node in root.iter()
                if node.get("id", "").startswith(("menu-normal", "menu-shadow")))
    # Remove the broad client fill, but preserve the subtle edge highlights
    # and shadow details in the nine-slice menu frame.
    set_surface_fill(root, ("menu-normal",), opacity, color)
    if wallpaper == "MacTahoe" and is_dark:
        clear_menu_client_fill(root)
        soften_menu_frame(root)
    _write_svg(path, root)
