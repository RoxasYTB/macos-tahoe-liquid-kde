import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "src/offline/plasma-theme/plasma-menu-overlay/refresh.py"
SPEC = importlib.util.spec_from_file_location("plasma_menu_overlay_refresh", SCRIPT)
OVERLAY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(OVERLAY)

WATCHER_SCRIPT = SCRIPT.with_name("blur_watch.py")
WATCHER_SPEC = importlib.util.spec_from_file_location("plasma_menu_blur_watch", WATCHER_SCRIPT)
WATCHER = importlib.util.module_from_spec(WATCHER_SPEC)
assert WATCHER_SPEC.loader is not None
WATCHER_SPEC.loader.exec_module(WATCHER)


def _write_module(root: Path, relative: Path, uri: str, menu_item: str, menu: str, separator: str) -> None:
    module = root / relative
    module.mkdir(parents=True)
    (module / "qmldir").write_text(
        f"module {uri}\nMenuItem 1.0 MenuItem.qml\nMenu 1.0 Menu.qml\nMenuSeparator 1.0 MenuSeparator.qml\nprefer :/qt/qml/unused/\n",
        encoding="utf-8",
    )
    for name, text in (("MenuItem.qml", menu_item), ("Menu.qml", menu), ("MenuSeparator.qml", separator)):
        (module / name).write_text(text, encoding="utf-8")


def _stock_modules(root: Path, plasma_prefix: str = '            prefix: "hover"') -> None:
    desktop_item = "\n".join((
        "    verticalPadding: Kirigami.Settings.hasTransientTouchInput ? 8 : 4 // Hardcoded to the Breeze theme value",
        "            Layout.preferredHeight: Kirigami.Settings.hasTransientTouchInput ? Kirigami.Units.iconSizes.smallMedium : Kirigami.Units.iconSizes.small",
        "            Layout.preferredWidth: Layout.preferredHeight",
        "    background: Rectangle {",
        "        implicitWidth: Kirigami.Units.gridUnit * 8",
        "        opacity: (controlRoot.highlighted || controlRoot.down) ? 1 : 0",
        "        color: controlRoot.pressed ? Kirigami.Theme.focusColor : Qt.alpha(Kirigami.Theme.focusColor, 0.3);",
        "        border.color: Kirigami.Theme.focusColor",
        "        border.width: 1",
        "        radius: Kirigami.Units.cornerRadius",
        "    }",
        '            color: controlRoot.pressed ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor',
    ))
    desktop_menu = '\n'.join((
        '    delegate: MenuItem {}',
        '    verticalPadding: style.pixelMetric("menuvmargin")',
        '    horizontalPadding: style.pixelMetric("menuhmargin")',
        '    contentItem: ListView {',
        '        spacing: 0 // Hardcoded to the Breeze theme value',
        '    }',
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
    ))
    plasma_background = '''    background: Item {
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
    }'''.replace('            prefix: "hover"', plasma_prefix)
    plasma_item = "\n".join((
        "    leftPadding: highlight.margins.left\n    topPadding: highlight.margins.top\n    rightPadding: highlight.margins.right\n    bottomPadding: highlight.margins.bottom",
        "            Layout.preferredHeight: Math.max(label.height, Kirigami.Units.iconSizes.small)",
        "            Layout.preferredWidth: Layout.preferredHeight",
        "            font: controlRoot.font\n            elide: Text.ElideRight",
        plasma_background,
    ))
    plasma_menu = "\n".join((
        '    topPadding: (background as KSvg.FrameSvgItem)?.margins.top ?? undefined\n    leftPadding: (background as KSvg.FrameSvgItem)?.margins.left ?? undefined\n    rightPadding: (background as KSvg.FrameSvgItem)?.margins.right ?? undefined\n    bottomPadding: (background as KSvg.FrameSvgItem)?.margins.bottom ?? undefined',
        '    delegate: MenuItem { width: parent.width; onImplicitWidthChanged: control.contentItem.contentItem.childrenChanged() }',
        '    contentItem: ListView {', '        model: control.contentModel', '    }',
        '''    background: KSvg.FrameSvgItem {
        imagePath: "widgets/background"
        implicitWidth: Kirigami.Units.gridUnit * 8
        implicitHeight: Kirigami.Units.gridUnit * 2
    }''',
    ))
    separator = '    verticalPadding: Math.round(Kirigami.Units.smallSpacing / 2)'
    _write_module(root, OVERLAY.MODULES["org.kde.desktop"], "org.kde.desktop", desktop_item, desktop_menu, separator)
    _write_module(root, OVERLAY.MODULES["org.kde.plasma.components"], "org.kde.plasma.components", plasma_item, plasma_menu, separator)


def test_overlay_patches_both_menu_engines_and_is_idempotent(tmp_path):
    source, overlay = tmp_path / "system-qml", tmp_path / "user-qml"
    _stock_modules(source)
    assert OVERLAY.refresh(source, overlay, profile_path=None) is True
    desktop = overlay / OVERLAY.MODULES["org.kde.desktop"]
    plasma = overlay / OVERLAY.MODULES["org.kde.plasma.components"]
    assert "prefer " not in (desktop / "qmldir").read_text(encoding="utf-8")
    desktop_item = (desktop / "MenuItem.qml").read_text(encoding="utf-8")
    assert "Qt.rgba(0.541176, 0.552941, 0.580392, 0.2600)" in desktop_item
    assert "Qt.rgba(0.333333, 0.466667, 0.839216, 1.0000)" in desktop_item
    assert 'color: "#F2EAF1"' in desktop_item
    assert "verticalPadding: Kirigami.Settings.hasTransientTouchInput ? 8 : 2" in desktop_item
    assert "Layout.preferredHeight: 12" in desktop_item
    desktop_menu = (desktop / "Menu.qml").read_text(encoding="utf-8")
    assert "spacing: 3" in desktop_menu
    assert "horizontalPadding: 0" in desktop_menu
    assert "radius: 12.0" in desktop_menu
    assert "anchors.margins: 0.75" in desktop_menu
    assert "Qt.rgba(0, 0, 0, 0.18)" in desktop_menu
    assert "Qt.rgba(1, 1, 1, 0.22)" in desktop_menu
    assert "Qt.rgba(0.000000, 0.000000, 0.000000, 0.4800)" in desktop_menu
    plasma_item = (plasma / "MenuItem.qml").read_text(encoding="utf-8")
    assert "readonly property bool tahoeSubmenuOpen" in plasma_item
    assert "tahoeSubmenuOpen && !controlRoot.hovered" in plasma_item
    assert "Qt.rgba(0.541176, 0.552941, 0.580392, 0.2600)" in plasma_item
    assert "Layout.preferredHeight: 12" in plasma_item
    plasma_menu = (plasma / "Menu.qml").read_text(encoding="utf-8")
    assert "radius: 12.0" in plasma_menu
    assert "anchors.margins: 0.75" in plasma_menu
    assert "Qt.rgba(0, 0, 0, 0.18)" in plasma_menu
    assert "Qt.rgba(1, 1, 1, 0.22)" in plasma_menu
    assert "Qt.rgba(0.000000, 0.000000, 0.000000, 0.4800)" in plasma_menu
    assert "verticalPadding: 5" in (plasma / "MenuSeparator.qml").read_text(encoding="utf-8")
    assert OVERLAY.refresh(source, overlay, profile_path=None) is False


def test_unknown_plasma_component_is_preserved(tmp_path):
    source, overlay = tmp_path / "system-qml", tmp_path / "user-qml"
    _stock_modules(source, '            prefix: "unexpected"')
    with pytest.raises(RuntimeError, match="refusing an unsafe patch"):
        OVERLAY.refresh(source, overlay, profile_path=None)
    assert not overlay.exists()


def test_strip_overlay_import_path_preserves_other_paths(tmp_path):
    overlay = tmp_path / "qml"
    current = f"/first:{overlay}:/second:{overlay}"
    assert OVERLAY.strip_overlay_path(current, overlay) == "/first:/second"


def test_blur_region_is_rounded_and_symmetric():
    region = WATCHER.rounded_region(120, 80, 6)
    rows = [region[offset:offset + 4] for offset in range(0, len(region), 4)]
    assert len(rows) == 80
    assert rows[0][0] > 0
    assert rows[0][2] < 120
    assert rows[6] == [0, 6, 120, 1]
    assert rows == list(reversed([[x, 79 - y, width, height] for x, y, width, height in rows]))


def test_popup_region_uses_painted_corner_radius_not_blur_setting(tmp_path):
    profile = tmp_path / "ABC.json"
    profile.write_text('{"blur":6,"cornerRadius":9}', encoding="utf-8")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(WATCHER, "PROFILE", profile)
    try:
        assert WATCHER._profile_region_radius() == 9
    finally:
        monkeypatch.undo()


def test_plasma_popup_region_uses_full_window_bounds():
    region = WATCHER.rounded_region(120, 80, 9)
    assert region[:4] == [7, 0, 106, 1]
    assert region[8 * 4:9 * 4] == [1, 8, 118, 1]
    assert region[-4:] == [7, 79, 106, 1]


def test_profile_change_refreshes_qml_surface_and_states(tmp_path):
    source, overlay = tmp_path / "system-qml", tmp_path / "user-qml"
    profile_path = tmp_path / "ABC.json"
    _stock_modules(source)
    profile_path.write_text(
        '{"backgroundMode":"black","backgroundColor":"#000000","backgroundOpacity":55,'
        '"cornerRadius":9,"hoverColor":"#5577D6","hoverOpacity":100,'
        '"submenuParentColor":"#8A8D94","parentOpacity":26,"textColor":"#F2EAF1"}',
        encoding="utf-8",
    )
    assert OVERLAY.refresh(source, overlay, profile_path) is True
    assert OVERLAY.refresh(source, overlay, profile_path) is False
    profile_path.write_text(
        '{"backgroundMode":"black","backgroundColor":"#000000","backgroundOpacity":60,'
        '"cornerRadius":17,"hoverColor":"#123456","hoverOpacity":80,'
        '"submenuParentColor":"#654321","parentOpacity":30,"textColor":"#EEEEEE"}',
        encoding="utf-8",
    )
    assert OVERLAY.refresh(source, overlay, profile_path) is True
    desktop = overlay / OVERLAY.MODULES["org.kde.desktop"]
    assert "0.6000" in (desktop / "Menu.qml").read_text(encoding="utf-8")
    assert "radius: 17.0" in (desktop / "Menu.qml").read_text(encoding="utf-8")
    assert '#EEEEEE' in (desktop / "MenuItem.qml").read_text(encoding="utf-8")


def test_default_profile_matches_live_translucent_menu():
    profile = OVERLAY._load_profile(None)
    assert profile["backgroundOpacity"] == 48
    assert profile["cornerRadius"] == 12
    assert WATCHER._profile_region_radius() == 12


def test_plasma_menu_overlay_path_reaches_current_shell_restart(monkeypatch, tmp_path):
    from steps import plasma_theme

    overlay = tmp_path / "plasma-menu-qml"
    manager_environment = {"QML_IMPORT_PATH": "/other/qml"}

    def run_user(command, **_kwargs):
        if command[2] == "show-environment":
            stdout = "".join(f"{key}={value}\n" for key, value in manager_environment.items())
            return SimpleNamespace(returncode=0, stdout=stdout)
        if command[2] == "set-environment":
            key, _, value = command[3].partition("=")
            manager_environment[key] = value
        elif command[2] == "unset-environment":
            manager_environment.pop(command[3], None)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(plasma_theme, "_MENU_STYLE_OVERLAY", overlay)
    monkeypatch.setattr(plasma_theme, "run_user", run_user)
    monkeypatch.delenv("QML_IMPORT_PATH", raising=False)

    plasma_theme._set_session_qml_import_path(True)
    expected = f"{overlay}:/other/qml"
    assert os.environ["QML_IMPORT_PATH"] == expected
    assert manager_environment["QML_IMPORT_PATH"] == expected

    plasma_theme._set_session_qml_import_path(False)
    assert os.environ["QML_IMPORT_PATH"] == "/other/qml"
    assert manager_environment["QML_IMPORT_PATH"] == "/other/qml"


def test_plasma_menu_login_hook_updates_activation_environments(tmp_path, monkeypatch):
    from steps import plasma_theme

    monkeypatch.setattr(plasma_theme, "_MENU_STYLE_OVERLAY", tmp_path / "qml")
    contents = plasma_theme._menu_style_env_contents()
    assert 'systemctl --user set-environment "QML_IMPORT_PATH=${QML_IMPORT_PATH}"' in contents
    assert "dbus-update-activation-environment --systemd QML_IMPORT_PATH" in contents
