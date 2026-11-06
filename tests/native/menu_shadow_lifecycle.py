#!/usr/bin/env python3
"""Manual probe: run only on a private X11 display with the compiled style."""
import json
import math
import os
import subprocess
import sys
from PyQt6.QtCore import QObject, QPoint, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QMenu

if os.environ.get("MTTKDE_PRIVATE_SHADOW_PROBE") != "1":
    raise SystemExit("Run only in a private display with MTTKDE_PRIVATE_SHADOW_PROBE=1")

app = QApplication(sys.argv)
app.setStyle('kvantum')
menu = QMenu()
menu.addAction('Native shadow lifecycle')
menu.addAction('Second action')
records = []


def query():
    return subprocess.check_output(
        ['xprop', '-id', str(int(menu.winId())), '_KDE_NET_WM_SHADOW'], text=True)


def created(stage):
    window = menu.windowHandle()
    shadow = window.findChild(QObject, '_kvantum_menu_shadow', Qt.FindChildOption.FindDirectChildrenOnly)
    assert shadow is not None, 'The native shadow QObject was not created'
    data = query()
    assert '(CARDINAL)' in data, data
    values = [int(value.strip()) for value in data.split('=', 1)[1].split(',')]
    assert len(values) == 12 and all(values[:8]), data
    surface = menu.property('_kvantum_menu_surface').adjusted(-1, -1, 1, 1)
    assert shadow.property('surface') == surface
    scale = window.devicePixelRatio()
    assert shadow.property('scale') == scale
    rounded = lambda value: math.floor(value * scale + 0.5)
    expected = [rounded(20 - surface.top()),
                rounded(20 - (menu.width() - surface.right() - 1)),
                rounded(20 - (menu.height() - surface.bottom() - 1)),
                rounded(20 - surface.left())]
    assert values[8:] == expected, (values[8:], expected)
    records.append({'stage': stage, 'scale': scale, 'padding': values[8:],
                    'surface': list(surface.getRect())})


def guarded(callback):
    def run():
        try:
            callback()
        except Exception as error:
            print(json.dumps({'error': str(error), 'records': records}), flush=True)
            app.exit(1)
    return run


def first():
    created('initial')
    app.setStyle('fusion')
    QTimer.singleShot(150, guarded(cleared))


def cleared():
    assert '(CARDINAL)' not in query(), 'Style change left a native shadow property behind'
    assert menu.windowHandle().findChild(QObject, '_kvantum_menu_shadow') is None
    records.append({'stage': 'fusion', 'shadow_removed': True})
    app.setStyle('kvantum')
    menu.popup(QPoint(600, 100))
    QTimer.singleShot(500, guarded(recreated))


def recreated():
    created('recreated')
    menu.resize(menu.width() + 20, menu.height() + 10)
    QTimer.singleShot(300, guarded(resized))


def resized():
    created('resized')
    app.setStyle('fusion')
    assert '(CARDINAL)' not in query()
    print(json.dumps({'passed': True, 'records': records}), flush=True)
    app.quit()


menu.popup(QPoint(600, 100))
QTimer.singleShot(700, guarded(first))
QTimer.singleShot(10000, lambda: app.exit(2))
sys.exit(app.exec())
