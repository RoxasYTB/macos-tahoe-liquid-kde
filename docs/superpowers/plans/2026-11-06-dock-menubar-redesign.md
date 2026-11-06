# Tahoe Dock and Menu Bar Redesign Plan

> **For agentic workers:** Execute this plan inline and verify each visual batch in an isolated Plasma session before considering a live panel refresh.

**Goal:** Bring the KDE dock and top menu bar closer to the supplied macOS reference while preserving the user's app pins, running apps, locale and working desktop session.

**Architecture:** Tune the existing Plasma layout and its existing global-menu/task-manager applets. Compare the supplied Linux screenshot at 1920x1080 with the macOS screenshot normalized from 3840x2160 to 1920x1080. Change reusable style/layout parameters only when the captures demonstrate a real mismatch; keep dynamic app/menu/tray content supplied by the current host.

**Tech Stack:** KDE Plasma 6, Qt Quick/QML, Plasma scripting layout, the Tahoe theme's global menu and icon task manager.

## Global Constraints

- Keep the user's current pinned applications and running applications.
- Do not translate the user's locale or replace active application menus with reference text.
- Do not move/resize active windows or restart Plasma/KWin.
- Preserve multi-screen layout behavior and existing per-screen task filtering.
- Keep changes local; no pull request until the complete project is ready.

---

### Task 1: Measure reference and current visuals

**Files:**
- `src/offline/layouts/mac-tahoe.js`
- `src/offline/plasmoids/org.kde.mac.tahoe.liquid.globalmenu/qml/{main.qml,MenuDelegate.qml}`
- `src/offline/plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/ui/{main.qml,Task.qml,LayoutMetrics.js}`
- Reference captures: `/tmp/user/1000/codex-clipboard-4173e785-e74f-4811-bb03-f9dea7f3002b.png` and `/tmp/user/1000/codex-clipboard-931fe2f3-8b55-4973-b7a8-445ec88b31d8.png`.

- [x] Normalize the macOS reference to 1920x1080 and compare panel height, baseline, dock bounds, icon sizes, item count and menu-label gaps.
- [x] Separate style differences from content differences (active apps, translated menu labels, and available tray items).
- [x] Record the baseline and selected decisions in `tests/native/dock_menubar_visual_validation.md`.

### Task 2: Apply one targeted visual batch

**Files:** `src/offline/layouts/mac-tahoe.js`, global-menu QML, and task-manager QML only where Task 1 demonstrates a mismatch.

- [x] Preserve the 32 px/68 px panel geometry; remove the extra App Grid dock widget, expose relevant active tray entries, and tighten global-menu typography/spacing.
- [x] Keep task hit areas and user app pins stable; no icon painted geometry was changed.
- [x] Run `git diff --check`, syntax-check all layout scripts, and build the global-menu/task-manager packages in isolated directories.

### Task 3: Capture and checkpoint

**Files:** `tests/native/dock_menubar_visual_validation.md` and affected package files.

- [ ] Render the changed layout in an isolated Plasma session at 1920x1080 and capture menu bar and dock states.
- [ ] Compare the result to the normalized reference, preserve app pins and multi-screen behavior, and record concrete remaining differences.
- [ ] Commit and push a scoped checkpoint only after the isolated visual capture is inspected; do not refresh the active user's panel in the middle of their session.

**Checkpoint:** The initial private Plasma sessions applied the machine's first-run/theme setup and showed KDE Welcome Center instead of the intended panel state. Those captures are invalid for judging this batch. Source edits and package builds are complete; the isolated visual render remains open.
