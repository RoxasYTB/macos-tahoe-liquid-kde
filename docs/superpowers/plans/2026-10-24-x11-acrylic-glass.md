# X11 Acrylic Glass Implementation Plan

> **For agentic workers:** Execute inline with focused review checkpoints. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and install the theme's existing Acrylic Glass KWin backend for X11, alongside Wayland when each SDK is available.

**Architecture:** Keep the bundled effect as the single source of truth. Enable CMake's existing optional KWin X11 target, include it in build verification only when the SDK produces it, and install it into KWin's X11 plugin directory using the existing versioned-binary safety pattern. Preserve the existing Wayland flow and shared configuration.

**Tech Stack:** CMake, C++/KWin effect plugin, Python installer, pytest.

## Global Constraints

- Preserve Plasma 6.6, 6.7, and 6.8 ABI selection independently for X11 and Wayland.
- Do not install or activate the external Glass fork; its current X11 compatibility is pinned to a Plasma 6.5 commit.
- Do not create or publish a pull request until the user explicitly approves.
- Keep upgrades safe for KWin's resident shared libraries and retain the current versioned install/activation pattern.

---

### Task 1: Build and package the X11 backend

**Files:**
- Modify: `src/offline/kwin-effects/acrylic-glass/CMakeLists.txt`
- Modify: `src/offline/kwin-effects/acrylic-glass/src/CMakeLists.txt`
- Modify: `src/scripts/steps/acrylic_glass.py`
- Modify: `tests/test_acrylic_glass_cmake.py`
- Modify: `tests/test_distro_packages.py` if an X11 SDK dependency mapping is required.

**Interfaces:**
- CMake keeps `liquidglass` as the Wayland module and emits an X11 module only when `KWinX11` development files are present.
- `build_artifacts()` reports every backend artifact actually configured for the build.
- `install()` places the X11 module under `<qt6-plugins>/kwin-x11/effects/plugins` and continues to install the shared KCM and Wayland module as before.

- [x] Add regression coverage for enabling the X11 target, optional SDK behavior, and installation destination.
- [x] Enable X11 backend detection by default without making Wayland-only systems fail configuration.
- [x] Add X11 installation through the existing versioned plugin-safety helpers.
- [x] Run focused CMake/installer tests and a local CMake build against the host's Plasma 6.7.4 X11 SDK.
- [x] Review the diff and report exact validation; do not publish a PR.
