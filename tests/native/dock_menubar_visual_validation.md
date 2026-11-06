# Dock and menu bar visual comparison

Date: 2026-11-06

## Reference pair

- Rebecca/KDE: `/tmp/user/1000/codex-clipboard-4173e785-e74f-4811-bb03-f9dea7f3002b.png` (1920x1080).
- macOS: `/tmp/user/1000/codex-clipboard-931fe2f3-8b55-4973-b7a8-445ec88b31d8.png` (3840x2160; compare at half scale).
- Initial strip comparison: `/tmp/tahoe-dock-menubar-reference-baseline.png`.

## Measured decisions

- Preserve the 32 px menu bar and 68 px dock panel; their apparent heights already match the normalized macOS capture.
- Remove the separate App Grid/Launchpad widget from the dock layouts: the reference starts with Finder, and Rebecca already has Dolphin pinned as its file-manager equivalent. Preserve all existing app pins and running windows.
- Show active notification, media, Chrome, Discord, Steam and Spotify tray entries in the visible menu-bar zone, alongside the existing Bluetooth, network, brightness and sound controls. Hardware and app tray content remains host-dependent.
- Reduce global-menu item labels from DemiBold to Medium and reduce horizontal padding from `largeSpacing` to `largeSpacing - round(smallSpacing/2)` (9 px at Rebecca's current Kirigami spacing). Keep the active application's name at its existing ExtraBold weight.

## Build checks and remaining verification

- `node --check` passed for the multi-screen layout and both light/dark layout scripts.
- `git diff --check` passed.
- The global-menu and task-manager CMake targets both built successfully in isolated `/tmp` build directories. The QML sources were processed by Qt's QML cache generator.
- The active Plasma panels were not refreshed or restarted. An isolated Plasma screenshot after these source changes is still required before calling this visual batch final.
- The first private Plasma capture was invalid: the fresh session applied its own first-run/theme layout and opened KDE Welcome Center over the panels. A second private attempt still captured the Welcome Center rather than the new dock/menu. No conclusion about the updated QML's rendered appearance is drawn from those images.
