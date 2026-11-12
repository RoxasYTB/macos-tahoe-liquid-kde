#!/usr/bin/env python3
# Managed by mac-tahoe-liquid-kde: Plasma QML menu overlay
"""Create a per-user Plasma Components QML overlay for Tahoe menu states."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


PATCH_VERSION = 13
MARKER = ".mac-tahoe-liquid-kde-overlay.json"
PROFILE_PATH = Path.home() / ".config/mac-tahoe-liquid-kde/context-menu-profiles/ABC.json"
MODULES = {
    "org.kde.desktop": Path("org/kde/desktop"),
    "org.kde.plasma.components": Path("org/kde/plasma/components"),
}


def _qml_root() -> Path:
    result = subprocess.run(
        ["qtpaths6", "--query", "QT_INSTALL_QML"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def strip_overlay_path(value: str, overlay_root: Path) -> str:
    overlay = str(overlay_root)
    return ":".join(part for part in value.split(":") if part and part != overlay)


def _source_fingerprint(source: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        digest.update(path.relative_to(source).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _is_owned(module: Path) -> bool:
    marker = module / MARKER
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return data.get("owner") == "mac-tahoe-liquid-kde"
    except (OSError, ValueError, AttributeError):
        return False


def _replace_once(path: Path, before: str, after: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(before) != 1:
        raise RuntimeError(f"Unexpected Plasma {description} source; refusing an unsafe patch")
    path.write_text(text.replace(before, after), encoding="utf-8")


def _qml_color(value: str, opacity: float = 1.0) -> str:
    value = value.lstrip("#")
    if len(value) != 6:
        raise RuntimeError("Invalid context-menu profile color")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    alpha = max(0.0, min(1.0, float(opacity)))
    return f"Qt.rgba({red / 255:.6f}, {green / 255:.6f}, {blue / 255:.6f}, {alpha:.4f})"


def _load_profile(path: Path | None) -> dict[str, object]:
    if path is None or not path.is_file():
        return {
            "backgroundMode": "black", "backgroundColor": "#000000", "backgroundOpacity": 48,
            "cornerRadius": 12, "hoverColor": "#5577D6", "hoverOpacity": 100,
            "submenuParentColor": "#8A8D94", "parentOpacity": 26, "textColor": "#F2EAF1",
        }
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Cannot read context-menu profile {path}: {exc}") from exc
    return profile


def _surface_color(profile: dict[str, object]) -> str:
    mode = str(profile.get("backgroundMode", "black"))
    color = str(profile.get("backgroundColor", "#000000"))
    opacity = float(profile.get("backgroundOpacity", 48)) / 100
    if mode == "transparent":
        opacity = 0
    elif mode == "black":
        color = "#000000"
    elif mode == "gray":
        color = "#808080"
    elif mode != "color":
        raise RuntimeError(f"Invalid context-menu background mode: {mode}")
    return _qml_color(color, opacity)


def _patch_module(module_name: str, target: Path, fingerprint: str, profile: dict[str, object]) -> None:
    qmldir = target / "qmldir"
    if not qmldir.is_file():
        raise RuntimeError(f"Missing Plasma Components qmldir: {qmldir}")
    lines = qmldir.read_text(encoding="utf-8").splitlines()
    if f"module {module_name}" not in lines:
        raise RuntimeError("Unexpected QML module URI; refusing to overlay it")
    if not any(line.startswith("MenuItem ") and line.endswith("MenuItem.qml") for line in lines):
        raise RuntimeError("Plasma Components MenuItem.qml is not registered; refusing to overlay it")
    # The system module prefers its compiled-in QML resources over disk files.
    # Removing that directive in our mirror makes the patched MenuItem.qml load.
    qmldir.write_text("\n".join(line for line in lines if not line.startswith("prefer ")) + "\n", encoding="utf-8")


    hover_color = str(profile.get("hoverColor", "#5577D6"))
    parent_color = str(profile.get("submenuParentColor", "#8A8D94"))
    text_color = str(profile.get("textColor", "#F2EAF1"))
    hover_opacity = float(profile.get("hoverOpacity", 100)) / 100
    parent_opacity = float(profile.get("parentOpacity", 26)) / 100
    radius = max(0, float(profile.get("cornerRadius", 12)))
    item_radius = max(0, float(profile.get("itemRadius", 5)))
    row_gap = max(0, float(profile.get("rowGap", 3)))
    root_vertical_padding = max(0, float(profile.get("rootVerticalPadding", 4)))
    root_width = max(100, float(profile.get("menuWidth", 187)))
    root_font_size = max(8, float(profile.get("rootTextSize", 13.2)))
    # Use the same single menu fill and two keylines as the live Kvantum QMenu.
    # A second inset fill creates a visible side band absent from Kvantum.

    if module_name == "org.kde.desktop":
        _replace_once(
            target / "MenuItem.qml",
            '    verticalPadding: Kirigami.Settings.hasTransientTouchInput ? 8 : 4 // Hardcoded to the Breeze theme value',
            '    verticalPadding: Kirigami.Settings.hasTransientTouchInput ? 8 : 2',
            "desktop MenuItem vertical padding",
        )
        _replace_once(
            target / "MenuItem.qml",
            '            Layout.preferredHeight: Kirigami.Settings.hasTransientTouchInput ? Kirigami.Units.iconSizes.smallMedium : Kirigami.Units.iconSizes.small',
            '            Layout.preferredHeight: 12',
            "desktop MenuItem icon size",
        )
        _replace_once(
            target / "MenuItem.qml",
            '            Layout.preferredWidth: Layout.preferredHeight',
            '            Layout.preferredWidth: 12',
            "desktop MenuItem icon column",
        )
        _replace_once(
            target / "MenuItem.qml",
            '''    background: Rectangle {
        implicitWidth: Kirigami.Units.gridUnit * 8
        opacity: (controlRoot.highlighted || controlRoot.down) ? 1 : 0
        color: controlRoot.pressed ? Kirigami.Theme.focusColor : Qt.alpha(Kirigami.Theme.focusColor, 0.3);
        border.color: Kirigami.Theme.focusColor
        border.width: 1
        radius: Kirigami.Units.cornerRadius
    }''',
            f'''    background: Rectangle {{
        implicitWidth: Kirigami.Units.gridUnit * 8
        readonly property bool tahoeSubmenuOpen: controlRoot.subMenu && controlRoot.subMenu.visible
        opacity: (controlRoot.highlighted || controlRoot.down || tahoeSubmenuOpen) ? 1 : 0
        color: tahoeSubmenuOpen && !controlRoot.hovered ? { _qml_color(parent_color, parent_opacity) } : { _qml_color(hover_color, hover_opacity) }
        border.width: 0
        radius: {float(profile.get('itemRadius', 5)):.1f}
    }}''',
            "desktop MenuItem background",
        )
        menu_item = target / "MenuItem.qml"
        _replace_once(menu_item,
                      'color: controlRoot.pressed ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor',
                      f'color: "{text_color}"', "desktop MenuItem text color")
        _replace_once(
            target / "Menu.qml",
            '    verticalPadding: style.pixelMetric("menuvmargin")',
            f'    verticalPadding: {root_vertical_padding:.1f}',
            "desktop Menu vertical margin",
        )
        _replace_once(
            target / "Menu.qml",
            '    horizontalPadding: style.pixelMetric("menuhmargin")',
            '    horizontalPadding: 0',
            "desktop Menu horizontal margin",
        )
        _replace_once(
            target / "Menu.qml",
            '        spacing: 0 // Hardcoded to the Breeze theme value',
            f'        spacing: {row_gap:.1f} // Tahoe ABC row gap',
            "desktop Menu row gap",
        )
        _replace_once(
            target / "Menu.qml",
            '''    background: Kirigami.ShadowedRectangle {
        radius: Kirigami.Units.cornerRadius
        implicitWidth: Kirigami.Units.gridUnit * 8
        color: Kirigami.Theme.backgroundColor

        border.color: Kirigami.ColorUtils.linearInterpolation(Kirigami.Theme.backgroundColor, Kirigami.Theme.textColor, Kirigami.Theme.frameContrast)
        border.width: 1

        shadow.xOffset: 0
        shadow.yOffset: 2
        shadow.color: Qt.rgba(0, 0, 0, 0.3)
        shadow.size: 8
    }''',
            f'''    background: Item {{
        implicitWidth: {root_width:.1f}
        Rectangle {{
            anchors.fill: parent
            antialiasing: true
            radius: {radius:.1f}
            color: {_surface_color(profile)}
        }}
        Rectangle {{
            anchors.fill: parent
            antialiasing: true
            radius: {radius:.1f}
            color: "transparent"
            border.color: Qt.rgba(0, 0, 0, 0.18)
            border.width: 0.75
        }}
        Rectangle {{
            anchors.fill: parent
            anchors.margins: 0.75
            antialiasing: true
            radius: {max(0, radius - 0.75):.1f}
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.22)
            border.width: 0.75
        }}
    }}''',
            "desktop Menu surface",
        )
        _replace_once(
            target / "Menu.qml",
            '    delegate: MenuItem {}',
            f'    delegate: MenuItem {{}}\n\n    font.pixelSize: {round(root_font_size)}',
            "desktop Menu font size",
        )
        _replace_once(
            target / "MenuSeparator.qml",
            '    verticalPadding: Math.round(Kirigami.Units.smallSpacing / 2)',
            '    verticalPadding: 5 // 11 px separator slot including the 1 px line',
            "desktop MenuSeparator slot",
        )
    else:
        _replace_once(
            target / "MenuItem.qml",
            '            Layout.preferredHeight: Math.max(label.height, Kirigami.Units.iconSizes.small)',
            '            Layout.preferredHeight: 12',
            "Plasma Components MenuItem icon size",
        )
        _replace_once(
            target / "MenuItem.qml",
            '            Layout.preferredWidth: Layout.preferredHeight',
            '            Layout.preferredWidth: 12',
            "Plasma Components MenuItem icon column",
        )
        _replace_once(
            target / "MenuItem.qml",
            '    leftPadding: highlight.margins.left\n    topPadding: highlight.margins.top\n    rightPadding: highlight.margins.right\n    bottomPadding: highlight.margins.bottom',
            f'    leftPadding: 0\n    topPadding: {root_vertical_padding / 2:.1f}\n    rightPadding: 0\n    bottomPadding: {root_vertical_padding / 2:.1f}',
            "Plasma Components MenuItem padding",
        )
        _replace_once(
            target / "MenuItem.qml",
            '            font: controlRoot.font\n            elide: Text.ElideRight',
            f'            font: controlRoot.font\n            color: "{text_color}"\n            elide: Text.ElideRight',
            "Plasma Components MenuItem text color",
        )
        _replace_once(
            target / "MenuItem.qml",
            '''    background: Item {
        implicitWidth: Kirigami.Units.gridUnit * 8

        KSvg.FrameSvgItem {
            id: highlight
            imagePath: "widgets/viewitem"
            prefix: "hover"
            anchors.fill: parent
            opacity: {
                if (controlRoot.highlighted || (controlRoot.enabled && controlRoot.hovered) || controlRoot.down) {
                    return 1
                } else {
                    return 0
                }
            }
            Behavior on opacity {
                enabled: Kirigami.Units.shortDuration > 0
                NumberAnimation {
                    duration: Kirigami.Units.shortDuration
                }
            }
        }
    }''',
            f'''    background: Rectangle {{
        implicitWidth: Kirigami.Units.gridUnit * 8
        readonly property bool tahoeSubmenuOpen: controlRoot.subMenu && controlRoot.subMenu.visible
        opacity: (controlRoot.highlighted || (controlRoot.enabled && controlRoot.hovered) || controlRoot.down || tahoeSubmenuOpen) ? 1 : 0
        color: tahoeSubmenuOpen && !controlRoot.hovered ? {_qml_color(parent_color, parent_opacity)} : {_qml_color(hover_color, hover_opacity)}
        radius: {item_radius:.1f}
        Behavior on opacity {{
            enabled: Kirigami.Units.shortDuration > 0
            NumberAnimation {{ duration: Kirigami.Units.shortDuration }}
        }}
    }}''',
            "Plasma Components MenuItem background",
        )
        _replace_once(
            target / "Menu.qml",
            '    topPadding: (background as KSvg.FrameSvgItem)?.margins.top ?? undefined\n    leftPadding: (background as KSvg.FrameSvgItem)?.margins.left ?? undefined\n    rightPadding: (background as KSvg.FrameSvgItem)?.margins.right ?? undefined\n    bottomPadding: (background as KSvg.FrameSvgItem)?.margins.bottom ?? undefined',
            f'    topPadding: {root_vertical_padding:.1f}\n    leftPadding: 0\n    rightPadding: 0\n    bottomPadding: {root_vertical_padding:.1f}',
            "Plasma Components Menu padding",
        )
        _replace_once(
            target / "Menu.qml",
            '        model: control.contentModel',
            f'        model: control.contentModel\n        spacing: {row_gap:.1f} // Tahoe ABC row gap',
            "Plasma Components Menu row gap",
        )
        _replace_once(
            target / "Menu.qml",
            '''    background: KSvg.FrameSvgItem {
        imagePath: "widgets/background"
        implicitWidth: Kirigami.Units.gridUnit * 8
        implicitHeight: Kirigami.Units.gridUnit * 2
    }''',
            f'''    background: Item {{
        implicitWidth: {root_width:.1f}
        Rectangle {{
            anchors.fill: parent
            antialiasing: true
            radius: {radius:.1f}
            color: {_surface_color(profile)}
        }}
        Rectangle {{
            anchors.fill: parent
            antialiasing: true
            radius: {radius:.1f}
            color: "transparent"
            border.color: Qt.rgba(0, 0, 0, 0.18)
            border.width: 0.75
        }}
        Rectangle {{
            anchors.fill: parent
            anchors.margins: 0.75
            antialiasing: true
            radius: {max(0, radius - 0.75):.1f}
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.22)
            border.width: 0.75
        }}
    }}''',
            "Plasma Components Menu surface",
        )
        _replace_once(
            target / "Menu.qml",
            '    delegate: MenuItem { width: parent.width; onImplicitWidthChanged: control.contentItem.contentItem.childrenChanged() }',
            f'    delegate: MenuItem {{ width: parent.width; onImplicitWidthChanged: control.contentItem.contentItem.childrenChanged() }}\n\n    font.pixelSize: {round(root_font_size)}',
            "Plasma Components Menu font size",
        )
        _replace_once(
            target / "MenuSeparator.qml",
            '    verticalPadding: Math.round(Kirigami.Units.smallSpacing / 2)',
            '    verticalPadding: 5 // 11 px separator slot including the 1 px line',
            "Plasma Components MenuSeparator slot",
        )
    (target / MARKER).write_text(json.dumps({
        "owner": "mac-tahoe-liquid-kde",
        "patch_version": PATCH_VERSION,
        "source_fingerprint": fingerprint,
    }, indent=2) + "\n", encoding="utf-8")


def refresh(source_root: Path, overlay_root: Path, profile_path: Path | None = PROFILE_PATH) -> bool:
    profile = _load_profile(profile_path)
    profile_fingerprint = hashlib.sha256(json.dumps(profile, sort_keys=True).encode("utf-8")).hexdigest()
    sources = {name: source_root / relative for name, relative in MODULES.items()}
    for name, source in sources.items():
        if not source.is_dir():
            raise RuntimeError(f"Plasma QML module not found ({name}): {source}")
    fingerprints = {name: _source_fingerprint(source) for name, source in sources.items()}
    targets = {name: overlay_root / relative for name, relative in MODULES.items()}
    owned = all(_is_owned(target) for target in targets.values())
    current_hashes = {}
    current_versions = {}
    if owned:
        for name, target in targets.items():
            try:
                metadata = json.loads((target / MARKER).read_text(encoding="utf-8"))
                current_hashes[name] = metadata.get("source_fingerprint")
                current_versions[name] = metadata.get("patch_version")
            except (OSError, ValueError, AttributeError):
                current_hashes[name] = None
                current_versions[name] = None
        if current_hashes == fingerprints and all(version == PATCH_VERSION for version in current_versions.values()):
            profile_hashes = {
                json.loads((target / MARKER).read_text(encoding="utf-8")).get("profile_fingerprint")
                for target in targets.values()
            }
            if profile_hashes == {profile_fingerprint}:
                return False
    elif overlay_root.exists() or overlay_root.is_symlink():
        raise RuntimeError(f"Unowned QML overlay exists; preserving it: {overlay_root}")

    overlay_root.parent.mkdir(parents=True, exist_ok=True)
    stage_parent = Path(tempfile.mkdtemp(prefix=".plasma-menu-overlay-", dir=overlay_root.parent))
    staged_root = stage_parent / "qml"
    try:
        for name, source in sources.items():
            staged_module = staged_root / MODULES[name]
            staged_module.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, staged_module)
            _patch_module(name, staged_module, fingerprints[name], profile)
            marker = staged_module / MARKER
            metadata = json.loads(marker.read_text(encoding="utf-8"))
            metadata["profile_fingerprint"] = profile_fingerprint
            marker.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        if overlay_root.exists():
            if not owned:
                raise RuntimeError(f"Unowned QML overlay exists; preserving it: {overlay_root}")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_root = overlay_root.parent / f"qml-overlay-backup-{stamp}"
            os.replace(overlay_root, backup_root)
        os.replace(staged_root, overlay_root)
    finally:
        shutil.rmtree(stage_parent, ignore_errors=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qml-root", type=Path, default=None)
    parser.add_argument("--overlay-root", type=Path, default=None)
    parser.add_argument("--profile", type=Path, default=PROFILE_PATH)
    parser.add_argument("--strip-import-path", action="store_true")
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    overlay_root = args.overlay_root or base / "qml"
    if args.strip_import_path:
        print(strip_overlay_path(os.environ.get("QML_IMPORT_PATH", ""), overlay_root))
        return 0
    try:
        changed = refresh(args.qml_root or _qml_root(), overlay_root, args.profile)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f"mac-tahoe-liquid-kde: Plasma menu overlay not applied: {exc}", file=sys.stderr)
        return 1
    if changed:
        print("mac-tahoe-liquid-kde: Plasma menu overlay refreshed", file=sys.stderr)
    print(overlay_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
