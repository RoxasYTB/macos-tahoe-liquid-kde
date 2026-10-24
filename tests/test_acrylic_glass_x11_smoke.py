"""Load a caller-provided Acrylic Glass X11 module in an isolated KWin."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest


def test_kwin_x11_loads_exact_acrylic_glass_module(tmp_path):
    plugin = os.environ.get("MTTKDE_X11_PLUGIN")
    if not plugin:
        pytest.skip("Set MTTKDE_X11_PLUGIN to a freshly built liquidglass_x11.so")
    plugin = Path(plugin).resolve()
    if not plugin.is_file():
        pytest.fail(f"X11 plugin does not exist: {plugin}")
    for binary in ("Xvfb", "xdpyinfo", "kwin_x11", "dbus-run-session", "qdbus6", "xwd"):
        if not shutil.which(binary):
            pytest.skip(f"{binary} required for isolated KWin X11 smoke test")

    root = tmp_path.resolve()
    expected_hash = hashlib.sha256(plugin.read_bytes()).hexdigest()
    script = r'''
root="$1"
source_plugin="$2"
plugins="$root/qt6/plugins/kwin-x11/effects/plugins"
mkdir -p "$plugins" "$root/config" "$root/data" "$root/cache" \
    "$root/home" "$root/runtime"
chmod 700 "$root/runtime"
cp "$source_plugin" "$plugins/liquidglass.so"
Xvfb -displayfd 1 -screen 0 1280x800x24 -nolisten tcp \
    >"$root/display" 2>"$root/xvfb.log" &
xvfb=$!
kwin=
cleanup() {
    [ -z "$kwin" ] || kill "$kwin" 2>/dev/null || true
    kill "$xvfb" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT
for _ in $(seq 1 100); do
    [ -s "$root/display" ] && break
    sleep 0.1
done
display=$(cat "$root/display")
export DISPLAY=":$display"
xdpyinfo >/dev/null
export QT_QPA_PLATFORM=xcb
export QT_PLUGIN_PATH="$root/qt6/plugins"
export QT_USE_PORTAL=0
export XDG_CONFIG_HOME="$root/config"
export XDG_DATA_HOME="$root/data"
export XDG_CACHE_HOME="$root/cache"
export XDG_RUNTIME_DIR="$root/runtime"
export HOME="$root/home"
kwin_x11 --replace --no-kactivities >"$root/kwin.log" 2>&1 &
kwin=$!
ready=false
for _ in $(seq 1 150); do
    if qdbus6 org.kde.KWin /KWin org.kde.KWin.supportInformation \
        >/dev/null 2>&1; then
        ready=true
        break
    fi
    kill -0 "$kwin" 2>/dev/null || break
    sleep 0.1
done
[ "$ready" = true ] || { cat "$root/kwin.log"; exit 1; }
loaded=$(qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.loadEffect liquidglass)
[ "$loaded" = true ] || { cat "$root/kwin.log"; exit 1; }
grep -Fxq true <(qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.isEffectLoaded liquidglass)
grep -Fxq true <(qdbus6 org.kde.KWin /Effects org.kde.kwin.Effects.isEffectSupported liquidglass)
grep -Fxq liquidglass <(qdbus6 org.kde.KWin /Effects org.freedesktop.DBus.Properties.Get org.kde.kwin.Effects activeEffects)
grep -Fxq true <(qdbus6 org.kde.KWin /Compositor org.freedesktop.DBus.Properties.Get org.kde.kwin.Compositing active)
grep -F "$plugins/liquidglass.so" "/proc/$kwin/maps" >/dev/null

# Exercise the X11 fallback with a real alpha-visual Plasma-class popup.
# Keep a vivid checkerboard behind it so the compositor output can be
# distinguished from the popup's own translucent fill.
cat >"$root/popup.cpp" <<'EOF'
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xrender.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
int main() {
    Display *display = XOpenDisplay(nullptr);
    if (!display) return 2;
    XVisualInfo query{};
    query.screen = DefaultScreen(display);
    int count = 0;
    XVisualInfo *visuals = XGetVisualInfo(display, VisualScreenMask, &query, &count);
    XVisualInfo *chosen = nullptr;
    XRenderPictFormat *format = nullptr;
    for (int i = 0; i < count && !chosen; ++i) {
        if (visuals[i].depth != 32) continue;
        auto *candidate = XRenderFindVisualFormat(display, visuals[i].visual);
        if (candidate && candidate->direct.alphaMask) {
            chosen = &visuals[i];
            format = candidate;
        }
    }
    if (!chosen || !format) return 3;
    XSetWindowAttributes attributes{};
    attributes.colormap = XCreateColormap(display, RootWindow(display, query.screen), chosen->visual, AllocNone);
    attributes.background_pixel = 0x99000000;
    attributes.border_pixel = 0;
    attributes.override_redirect = True;
    Window popup = XCreateWindow(display, RootWindow(display, query.screen), 380, 260, 460, 220, 0,
        chosen->depth, InputOutput, chosen->visual,
        CWColormap | CWBackPixel | CWBorderPixel | CWOverrideRedirect, &attributes);
    XClassHint classHint{const_cast<char*>("plasma-popup-probe"), const_cast<char*>("plasmashell")};
    XSetClassHint(display, popup, &classHint);
    Atom typeAtom = XInternAtom(display, "_NET_WM_WINDOW_TYPE", False);
    Atom menuAtom = XInternAtom(display, "_NET_WM_WINDOW_TYPE_POPUP_MENU", False);
    XChangeProperty(display, popup, typeAtom, XA_ATOM, 32, PropModeReplace,
        reinterpret_cast<unsigned char*>(&menuAtom), 1);
    XMapRaised(display, popup);
    XFlush(display);
    sleep(2);
    char *capture = std::getenv("MTTKDE_X11_CAPTURE");
    if (!capture) return 4;
    char command[4096];
    std::snprintf(command, sizeof(command), "xwd -silent -id %lu -out '%s'", popup, capture);
    int result = std::system(command);
    XDestroyWindow(display, popup);
    XCloseDisplay(display);
    return result == 0 ? 0 : 5;
}
EOF
g++ "$root/popup.cpp" -o "$root/popup" -lX11 -lXrender
MTTKDE_X11_CAPTURE="$root/popup.xwd" "$root/popup" >"$root/popup.log" 2>&1 &
popup_pid=$!
for _ in $(seq 1 40); do
    grep -F plasmashell "/proc/$kwin/maps" >/dev/null 2>&1 || true
    if xwininfo -root -tree 2>/dev/null | grep -q plasma-popup-probe; then break; fi
    sleep 0.1
done
window=$(xwininfo -root -tree | awk '/plasmashell/ {print $1; exit}')
[ -n "$window" ] || { cat "$root/popup.log"; cat "$root/kwin.log"; exit 1; }
xprop -id "$window" _NET_WM_WINDOW_TYPE | grep -q _NET_WM_WINDOW_TYPE_POPUP_MENU
wait "$popup_pid"
[ -s "$root/popup.xwd" ]
xwdtopnm "$root/popup.xwd" >"$root/popup.ppm"
grep -a -q 'P3\|P6' "$root/popup.ppm"
'''
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG")}
    log_path = root / "smoke.log"
    with log_path.open("w") as log:
        result = subprocess.run(
            ["dbus-run-session", "--", "bash", "-euc", script, "x11-smoke",
             str(root), str(plugin)],
            env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90,
        )
    assert result.returncode == 0, log_path.read_text(encoding="utf-8")
    assert hashlib.sha256(plugin.read_bytes()).hexdigest() == expected_hash
