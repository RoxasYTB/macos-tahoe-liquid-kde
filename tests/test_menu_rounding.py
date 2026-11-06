"""Kvantum selection curvature must never change menu layout at any scale."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("mode", ["", "Dark"])
@pytest.mark.parametrize("scale", ["1", "1.5", "2"])
def test_native_rounding_ignores_theme_frame_expansion(repo, tmp_path, mode, scale):
    pytest.importorskip("PyQt6.QtWidgets")
    results = []
    for expansion in (0, 12):
        home = tmp_path / str(expansion)
        config = home / ".config/Kvantum"
        profile = "mac-tahoe-liquid-kde" + mode
        theme = config / profile
        theme.mkdir(parents=True)
        source = repo / "src/offline/kvantum/mac-tahoe-liquid-kde"
        shutil.copy2(source / f"{profile}.svg", theme)
        content = (source / f"{profile}.kvconfig").read_text()
        start = content.index("[MenuItem]")
        end = content.index("\n[", start + 1)
        content = content[:start] + content[start:end].replace(
            "frame.expansion=12", f"frame.expansion={expansion}") + content[end:]
        (theme / f"{profile}.kvconfig").write_text(content)
        (config / "kvantum.kvconfig").write_text(f"[General]\ntheme={profile}\n")
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "QT_PLUGIN_PATH")}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
                   QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic",
                   QT_SCALE_FACTOR=scale)
        result = subprocess.run([sys.executable, __file__, "--probe"], env=env,
                                capture_output=True, text=True, timeout=20)
        if result.returncode == 77:
            pytest.skip("Kvantum Qt6 style plugin required")
        assert result.returncode == 0, result.stdout + result.stderr
        results.append(json.loads(result.stdout))
    before, after = results
    assert after["geometry"] == before["geometry"]
    assert after["size"] == before["size"]
    # Native rows now share a fixed contour across root/child roles.
    assert after["top_inset"] == before["top_inset"]
    assert after["top_inset"] > 0
    assert after["center"] == before["center"]
    # The dark profile intentionally uses a translucent selected fill. Verify
    # that the rounded center is painted, without requiring an opaque pixel.
    assert after["center_alpha"] > 0


@pytest.mark.parametrize("mode", ["", "Dark"])
def test_submenu_overlap_accounts_for_both_transparent_shadow_margins(repo, mode):
    config = repo / "src/offline/kvantum/mac-tahoe-liquid-kde" / (
        f"mac-tahoe-liquid-kde{mode}.kvconfig"
    )
    general = config.read_text().split("[%General]", 1)[1].split("\n[", 1)[0]
    values = dict(line.split("=", 1) for line in general.splitlines() if "=" in line)
    # Qt places the child with an inclusive one-pixel menu overlap. Both
    # windows include their own transparent shadow margin: the visible glass
    # and the two dark keylines are outside the refractive glass plane.
    # The white glass planes must overlap by five pixels.
    visible_overlap = (
        int(values["submenu_overlap"]) + 1
        - 2 * int(values["menu_shadow_depth"]) - 2
    )
    assert visible_overlap == 5



def test_native_menu_style_preserves_application_margins(tmp_path):
    plugin_path = os.environ.get("MTTKDE_TEST_KVANTUM_PLUGIN_PATH")
    if not plugin_path:
        pytest.skip("compiled Tahoe Kvantum override required")
    pytest.importorskip("PyQt6.QtWidgets")
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG")}
    env.update(HOME=str(tmp_path), XDG_CONFIG_HOME=str(tmp_path / "config"),
               QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic",
               QT_PLUGIN_PATH=plugin_path)
    result = subprocess.run([sys.executable, __file__, "--margins-probe"], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def _margins_probe():
    from PyQt6.QtCore import QMargins
    from PyQt6.QtWidgets import QApplication, QMenu
    app = QApplication([])
    app.setStyle("fusion")
    root = QMenu()
    root.setContentsMargins(3, 4, 5, 6)
    child = root.addMenu("Child")
    child.setContentsMargins(1, 2, 3, 4)
    child.addAction("Item")
    menus = (root, child)
    originals = tuple(QMargins(menu.contentsMargins()) for menu in menus)
    app.setStyle("kvantum")
    for menu in menus:
        menu.ensurePolished()
    applied = tuple(QMargins(menu.contentsMargins()) for menu in menus)
    assert app.style().objectName().lower() == "kvantum"
    assert applied == originals, "The native style must preserve application contents margins"
    _check_native_selection_states(root, child, app)
    app.setStyle("fusion")
    assert tuple(menu.contentsMargins() for menu in menus) == originals
    app.setStyle("kvantum")
    for menu in menus:
        menu.ensurePolished()
    assert tuple(menu.contentsMargins() for menu in menus) == applied
    app.setStyle("fusion")
    assert tuple(menu.contentsMargins() for menu in menus) == originals


def _check_native_selection_states(root, child, app):
    from PyQt6.QtCore import QPoint, QRect
    from PyQt6.QtGui import QColor, QCursor, QImage, QPainter
    from PyQt6.QtWidgets import QStyle, QStyleOptionMenuItem
    root.show()
    child.setFixedSize(180, 80)
    child.move(root.mapToGlobal(QPoint(root.width() + 20, 0)))
    child.show()
    app.processEvents()
    option = QStyleOptionMenuItem()
    option.initFrom(child)
    option.menuItemType = QStyleOptionMenuItem.MenuItemType.Normal
    option.rect = QRect(0, 0, 160, 24)
    option.text = ""
    pointer = child.mapToGlobal(QPoint(80, 12))
    QCursor.setPos(pointer)
    assert QCursor.pos() == pointer

    def center(state, widget=child, rect=None, submenu=False):
        option.initFrom(widget)
        option.menuItemType = (QStyleOptionMenuItem.MenuItemType.SubMenu if submenu
                               else QStyleOptionMenuItem.MenuItemType.Normal)
        option.rect = QRect(0, 0, 160, 24) if rect is None else rect
        option.state = state
        image = QImage(180, 40, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter(image)
        painter.translate(-option.rect.left(), -option.rect.top())
        widget.style().drawControl(QStyle.ControlElement.CE_MenuItem, option, painter, widget)
        painter.end()
        return image.pixelColor(min(80, option.rect.width() // 2), option.rect.height() // 2)

    enabled = QStyle.StateFlag.State_Enabled
    selected = QStyle.StateFlag.State_Selected
    stale_hover = QStyle.StateFlag.State_MouseOver
    blue = QColor(85, 111, 196)
    # Keyboard selection must not leave the old pointer row highlighted.
    assert center(enabled).alpha() == 0
    # Disabled actions must remain visually disabled even if marked selected.
    assert center(selected).alpha() == 0
    assert center(enabled | selected) == blue

    parent_rect = root.actionGeometry(child.menuAction())
    QCursor.setPos(root.mapToGlobal(parent_rect.center()))
    assert center(enabled | selected, root, parent_rect, True) == blue
    QCursor.setPos(pointer)
    # Qt can leave State_MouseOver on the parent while its child has the pointer.
    inactive = center(enabled | selected | stale_hover, root, parent_rect, True)
    # Premultiplied storage can round translucent RGB channels by one level.
    assert inactive.alpha() == 140
    assert max(abs(actual - expected) for actual, expected in
               zip(inactive.getRgb()[:3], (148, 110, 131))) <= 1

    child.hide()
    leaf_rect = QRect(0, 0, 160, 24)
    QCursor.setPos(root.mapToGlobal(leaf_rect.center()))
    assert center(enabled | selected, root, leaf_rect) == blue
    assert center(enabled, root, leaf_rect).alpha() == 0
    assert center(selected, root, leaf_rect).alpha() == 0
    child.hide()
    root.hide()


def _probe():
    from PyQt6.QtCore import QRect, Qt
    from PyQt6.QtGui import QImage, QPainter, QPixmap, QIcon
    from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QStyleOptionMenuItem
    app = QApplication([])
    if not app.setStyle("kvantum"):
        sys.exit(77)
    menu = QMenu()
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.black)
    for label in ("About This Computer", None, "System Settings…", "App Store…",
                  None, "Force Quit…", None, "Sleep", "Restart…", "Shut Down…",
                  None, "Lock Screen", "Log Out Lester…"):
        menu.addSeparator() if label is None else menu.addAction(QIcon(pixmap), label)
    size = menu.sizeHint()
    geometry = [list(menu.actionGeometry(a).getRect()) for a in menu.actions()]
    option = QStyleOptionMenuItem()
    option.initFrom(menu)
    option.menuItemType = QStyleOptionMenuItem.MenuItemType.Normal
    option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Selected
    option.rect = QRect(0, 0, 200, menu.actionGeometry(menu.actions()[0]).height())
    scale = float(os.environ["QT_SCALE_FACTOR"])
    image = QImage(round(200 * scale), round(option.rect.height() * scale), QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(scale)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    menu.style().drawControl(QStyle.ControlElement.CE_MenuItem, option, painter, menu)
    painter.end()
    y = max(0, round(scale / 2))
    inset = next(x for x in range(image.width()) if image.pixelColor(x, y).alpha() > 0)
    center_color = image.pixelColor(image.width() // 2, image.height() // 2)
    center = center_color.rgba()
    print(json.dumps(dict(geometry=geometry, size=[size.width(), size.height()],
                         top_inset=inset, center=center,
                         center_alpha=center_color.alpha())))


if __name__ == "__main__":
    if "--margins-probe" in sys.argv:
        _margins_probe()
    else:
        _probe()
