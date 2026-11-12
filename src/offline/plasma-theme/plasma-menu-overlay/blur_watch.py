#!/usr/bin/env python3
# Managed by mac-tahoe-liquid-kde: Plasma QML menu blur watcher
"""Apply the ABC rounded KWin blur region to Plasma QML menu windows on X11."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sys

from Xlib import X, Xatom, display, error


CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
PROFILE = CONFIG_HOME / "mac-tahoe-liquid-kde/context-menu-profiles/ABC.json"
BLUR_PROPERTY = "_KDE_NET_WM_BLUR_BEHIND_REGION"


def _profile_region_radius() -> int:
    try:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        # The compositor uses this region as the actual popup mask, so it must
        # match the radius painted by the Plasma QML background. Blur strength
        # is an independent setting and must never change the corner geometry.
        return max(0, min(64, round(float(profile.get("cornerRadius", 12)))))
    except (OSError, ValueError, TypeError):
        return 0


def rounded_region(
    width: int, height: int, radius: int, margin_x: int = 0, margin_y: int = 0
) -> list[int]:
    """Return X11 CARDINAL rectangles approximating a rounded QRegion."""
    width, height = max(1, width), max(1, height)
    margin_x = min(max(0, margin_x), max(0, (width - 1) // 2))
    margin_y = min(max(0, margin_y), max(0, (height - 1) // 2))
    inner_width = max(1, width - 2 * margin_x)
    inner_height = max(1, height - 2 * margin_y)
    radius = min(max(0, radius), inner_width // 2, inner_height // 2)
    values: list[int] = []
    for y in range(inner_height):
        inset = 0
        if radius and y < radius:
            dy = radius - y - 0.5
            inset = max(0, math.ceil(radius - math.sqrt(max(0.0, radius * radius - dy * dy))))
        elif radius and y >= inner_height - radius:
            dy = y - (inner_height - radius) + 0.5
            inset = max(0, math.ceil(radius - math.sqrt(max(0.0, radius * radius - dy * dy))))
        values.extend((margin_x + inset, margin_y + y, max(1, inner_width - 2 * inset), 1))
    return values


class BlurWatcher:
    def __init__(self) -> None:
        self.connection = display.Display()
        self.root = self.connection.screen().root
        self.type_atom = self.connection.intern_atom("_NET_WM_WINDOW_TYPE")
        self.popup_atom = self.connection.intern_atom("_NET_WM_WINDOW_TYPE_POPUP_MENU")
        self.blur_atom = self.connection.intern_atom(BLUR_PROPERTY)
        self.cardinal_atom = self.connection.intern_atom("CARDINAL")
        self.managed: dict[int, tuple[int, int, int]] = {}
        self.expected: dict[int, list[int]] = {}
        self.root.change_attributes(event_mask=X.SubstructureNotifyMask)
        self.connection.sync()

    def update(self, window) -> bool:
        try:
            types = window.get_full_property(self.type_atom, Xatom.ATOM)
            if types is None or self.popup_atom not in types.value:
                return False
            if window.get_wm_class() != ("plasmashell", "plasmashell"):
                return False
            # Plasma can publish its own blur property just after MapNotify.
            # Subscribe before installing ours so a later replacement is
            # observed and corrected while the popup remains open.
            window.change_attributes(event_mask=X.PropertyChangeMask)
            geometry = window.get_geometry()
            radius = _profile_region_radius()
            if radius <= 0:
                return False
            current = window.get_full_property(self.blur_atom, X.AnyPropertyType)
            if current is not None and window.id not in self.managed:
                # Preserve regions installed by native Kvantum or another
                # Plasma component; manage only popups first seen without one.
                return False
            dimensions = (geometry.width, geometry.height, radius)
            # Plasma QML paints into the popup's own window bounds. Keep the
            # compositor mask on those same bounds; Kvantum's QMenu has its
            # own 2x1 transparent SVG frame and must not lend it to QML.
            values = rounded_region(geometry.width, geometry.height, radius)
            current_values = [int(value) for value in current.value] if current is not None else None
            if self.managed.get(window.id) == dimensions and current_values == self.expected.get(window.id):
                return False
            window.change_property(
                self.blur_atom, self.cardinal_atom, 32, values, X.PropModeReplace
            )
            self.connection.flush()
            self.managed[window.id] = dimensions
            self.expected[window.id] = values
            print(f"popup corner region set for Plasma window {window.id:#x} ({geometry.width}x{geometry.height}, regionRadius={radius}, inset=0)", flush=True)
            return True
        except (error.BadWindow, error.BadAccess):
            return False

    def run(self) -> None:
        for child in self.root.query_tree().children:
            self.update(child)
        while True:
            event = self.connection.next_event()
            if event.type == X.MapNotify:
                # Qt Quick publishes WM_CLASS and window type just before mapping.
                self.update(event.window)
            elif event.type == X.ConfigureNotify:
                self.update(event.window)
            elif event.type == X.PropertyNotify and event.atom == self.blur_atom:
                # Ignore our own PropertyNotify (current == expected); if
                # Plasma rewrote the CARDINAL list, restore the profile shape.
                self.update(event.window)
            elif event.type == X.DestroyNotify:
                self.managed.pop(event.window.id, None)
                self.expected.pop(event.window.id, None)


def main() -> int:
    if not os.environ.get("DISPLAY"):
        print("No X11 DISPLAY; Plasma blur watcher is inactive", file=sys.stderr)
        return 0
    try:
        BlurWatcher().run()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Plasma blur watcher stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
