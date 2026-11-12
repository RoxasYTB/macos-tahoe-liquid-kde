# Context menu styling at runtime

The ABC context menu profile is shared by the native Qt/Kvantum path and the
Plasma QML menu surfaces. These are separate rendering paths: installing the
assets and selecting the Kvantum theme is not enough if the running
`plasmashell` process was started without the user plugin and QML import paths.

## Installer activation

The installer prepares the user shell environment and the current session
before its final Plasma restart. At login, the generated Plasma environment
hooks also update both the systemd user manager and D-Bus activation
environment. This matters because a restarted shell may be launched by either
service manager rather than by the original installer process:

- `QT_PLUGIN_PATH` points first to the locally patched Kvantum plugin. The
  installer updates its own environment and the systemd user manager so the
  restarted shell inherits the same plugin path. Existing plugin paths are
  retained; uninstall removes only this theme's path.
- `QML_IMPORT_PATH` points first to the Plasma menu overlay. It is likewise
  merged into the installer process and systemd user environment before the
  restart, and uninstall removes only the overlay path.

This fixes the case where the theme files were installed but the current
Plasma shell continued to load the distribution's unpatched Kvantum plugin.
Dolphin and Plasma can then use the same installed Kvantum styling while QML
menus load the matching overlay assets.

## Runtime verification

After installing, restart Plasma (the installer does this as part of applying
the theme) and check the actual shell process, not just the configuration:

```sh
pid=$(pgrep -xo plasmashell)
tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(QT_PLUGIN_PATH|QML_IMPORT_PATH)='
grep -F 'libkvantum.so' "/proc/$pid/maps" | head
```

`libkvantum.so` should resolve to the user's theme overlay plugin directory,
and `QML_IMPORT_PATH` should include the installed `plasma-menu-style/qml`
overlay. Then open real context menus in Plasma and Dolphin, including a
submenu, to verify the rounded frame and selection state. The automated tests
cover environment propagation and cleanup; they do not replace this live UI
check.

## Screenshots

- [Provided visual reference](screenshots/reference-context-menu.png)
- [Live Plasma desktop context menu](screenshots/plasma-context-menu-live.png)

The live capture shows the real desktop menu after the user plugin path was
loaded. Its action list differs from the reference because it is Plasma's
desktop menu; the comparison demonstrates the shared rounded, translucent
surface and blue hover treatment, not identical menu contents.
