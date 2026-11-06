#!/usr/bin/env python3
"""Opt-in geometry checks on a private X11 display with the compiled style."""
import json
import os
import sys
import time
from PyQt6.QtCore import QEvent, QPoint, QRect, QTimer, Qt
from PyQt6.QtGui import QCursor, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMenu

if os.environ.get('MTTKDE_PRIVATE_MENU_PROBE') != '1':
    raise SystemExit('Run only in a private display with MTTKDE_PRIVATE_MENU_PROBE=1')
sys.argv[0] = 'plasmashell'
app = QApplication(sys.argv)
app.setStyle('kvantum')
root = QMenu()
root.addAction('First parent action')
root.addSeparator()
root.addAction('Second parent action')
child = root.addMenu('Submenu')
root.addAction('Last parent action')
triggered = []
first_action = child.addAction('First child action')
first_action.triggered.connect(lambda checked=False: triggered.append(True))
child.addSeparator()
child.addAction('Second child action')
area = app.primaryScreen().availableGeometry()
cases = [
    ('center', Qt.LayoutDirection.LeftToRight, QPoint(area.left() + 250, area.top() + 150)),
    ('right', Qt.LayoutDirection.LeftToRight, QPoint(area.right() - 20, area.top() + 150)),
    ('left-rtl', Qt.LayoutDirection.RightToLeft, QPoint(area.left() + 20, area.top() + 150)),
    ('bottom', Qt.LayoutDirection.LeftToRight, QPoint(area.left() + 250, area.bottom() - 20)),
]
records = []
index = 0
deadline = 0


def guarded(callback):
    def run():
        try:
            callback()
        except Exception as error:
            print(json.dumps({'error': str(error), 'records': records}), flush=True)
            app.exit(1)
    return run


def begin():
    global deadline
    if index == len(cases):
        print(json.dumps({'passed': True, 'records': records}), flush=True)
        app.quit()
        return
    name, direction, position = cases[index]
    app.setLayoutDirection(direction)
    root.setLayoutDirection(direction)
    child.setLayoutDirection(direction)
    root.popup(position)
    deadline = time.monotonic() + 3
    QTimer.singleShot(150, guarded(hover))


def hover():
    QCursor.setPos(root.mapToGlobal(root.actionGeometry(child.menuAction()).center()))
    QTimer.singleShot(350, guarded(check))


def plane(menu):
    rect = menu.property('_kvantum_menu_surface')
    assert isinstance(rect, QRect) and not rect.isEmpty(), 'No declared native glass plane'
    return rect.translated(menu.mapToGlobal(QPoint(0, 0)))


def check():
    global index
    if not child.isVisible():
        assert time.monotonic() < deadline, f'Submenu did not open: {cases[index][0]}'
        QTimer.singleShot(100, guarded(hover))
        return
    name, direction, position = cases[index]
    parent_plane, child_plane = plane(root), plane(child)
    overlap = parent_plane.intersected(child_plane).width()
    assert overlap == 5, (name, overlap, parent_plane.getRect(), child_plane.getRect())
    screen_area = child.screen().availableGeometry()
    assert screen_area.contains(child.geometry()), (name, child.geometry().getRect(), screen_area.getRect())
    parent_top = root.mapToGlobal(root.actionGeometry(child.menuAction()).topLeft()).y()
    child_top = child.mapToGlobal(child.actionGeometry(child.actions()[0]).topLeft()).y()
    if name != 'bottom':
        assert parent_top == child_top, (name, parent_top, child_top)
    record = {'case': name, 'scale': child.windowHandle().devicePixelRatio(),
              'root': list(root.geometry().getRect()), 'child': list(child.geometry().getRect()),
              'overlap': overlap, 'parent_row_y': parent_top, 'child_row_y': child_top}
    child.setActiveAction(first_action)
    before = len(triggered)
    app.sendEvent(child, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    app.sendEvent(child, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert len(triggered) == before + 1, 'Return did not trigger exactly one native QAction'
    record['return_triggered_once'] = True
    records.append(record)
    child.hide()
    root.hide()
    index += 1
    QTimer.singleShot(150, guarded(begin))


QTimer.singleShot(0, guarded(begin))
QTimer.singleShot(18000, lambda: app.exit(2))
sys.exit(app.exec())
