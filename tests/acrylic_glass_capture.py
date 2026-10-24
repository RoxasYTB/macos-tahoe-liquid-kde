#!/usr/bin/env python3
"""Opt-in, isolated KWin/Wayland pixel probe. Never installs on the desktop.

Uses a synthetic transparent VM surface; this is not a VirtualBox guest test.
Requires KWin, Spectacle, kscreen-doctor, qdbus6, PyQt6, Pillow and a compiled effect.
Use --backend xcb for Xwayland (also requires Xwayland).
Use --identity VirtualBox --expect changed to check the manager is not excluded.
Use --expect changed for an unpatched control; unchanged is the default.
The output directory must be new. No host config or plugins are modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def wait_for(check, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for isolated session")


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def client(role):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QPainter
    from PyQt6.QtWidgets import QApplication, QWidget

    app = QApplication(sys.argv)
    app.setDesktopFileName(os.environ["MTTKDE_CAPTURE_IDENTITY"] if role == "vm" else "capture-desktop")

    rounded = os.environ.get("MTTKDE_CAPTURE_EFFECT") == "kwin4_effect_shapecorners"

    class Surface(QWidget):
        def paintEvent(self, event):
            painter = QPainter(self)
            if role == "desktop":
                if os.environ.get("MTTKDE_CAPTURE_REFRACTION_PATTERN"):
                    colors = ("#e63946", "#f1fa8c", "#2a9d8f", "#457b9d",
                              "#9b5de5", "#f15bb5", "#00bbf9", "#ff9f1c")
                    for index, color in enumerate(colors):
                        left = index * self.width() // len(colors)
                        right = (index + 1) * self.width() // len(colors)
                        painter.fillRect(left, 0, right - left, self.height(), QColor(color))
                    painter.setPen(QColor("white"))
                    for offset in range(-self.height(), self.width(), 24):
                        painter.drawLine(offset, 0, offset + self.height(), self.height())
                else:
                    for y in range(0, self.height(), 16):
                        for x in range(0, self.width(), 16):
                            painter.fillRect(x, y, 16, 16,
                                             QColor("#214263" if (x // 16 + y // 16) % 2 else "#e1c787"))
            elif rounded:
                painter.fillRect(self.rect(), QColor("#3778aa"))
                if os.environ.get("MTTKDE_CAPTURE_COMPANION"):
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                    painter.fillRect(self.width() // 4, self.height() // 4,
                                     self.width() // 2, self.height() // 2, QColor(55, 120, 170, 100))
            else:
                painter.fillRect(self.width() // 3, self.height() // 3,
                                 self.width() // 3, self.height() // 3, QColor("#3778aa"))

    # Qt 6.10 does not map QWidget desktop windows on every Wayland backend.
    # The first fullscreen client supplies the background beneath the probe.
    flags = Qt.WindowType.Window if role == "vm" and rounded else Qt.WindowType.FramelessWindowHint
    window = Surface(None, flags)
    if role != "desktop":
        window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    window.setWindowTitle("Synthetic VM surface" if role == "vm" else "Capture background")
    if role == "vm" and os.environ.get("MTTKDE_CAPTURE_DESKTOP"):
        # Set the actual X11 desktop type before mapping on this private Xwayland.
        subprocess.run(["xprop", "-id", str(int(window.winId())), "-f", "_NET_WM_WINDOW_TYPE", "32a",
                        "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DESKTOP"], check=True, timeout=5)
    window.resize(960, 640)
    if role != "desktop" and rounded:
        window.resize(480, 320)
        window.show()
    else:
        window.showFullScreen()
    app.exec()


def session():
    output = Path(os.environ["MTTKDE_CAPTURE_DIR"])
    temporary = output / "session-env.tmp"
    temporary.write_text(json.dumps(dict(os.environ)))
    temporary.replace(output / "session-env.json")
    while True:
        time.sleep(1)


def assert_compositor_owner(pid):
    owner = subprocess.run([
        "qdbus6", "org.freedesktop.DBus", "/org/freedesktop/DBus",
        "org.freedesktop.DBus.GetConnectionUnixProcessID", "org.kde.KWin",
    ], capture_output=True, text=True, check=True, timeout=5)
    if int(owner.stdout.strip()) != pid:
        raise RuntimeError("D-Bus belongs to a different compositor; refusing mutations")


def inside(output):
    # Internal entry points must never accidentally operate on the real
    # desktop if invoked directly instead of through run().
    for key, expected in (("MTTKDE_CAPTURE_DIR", output),
                          ("HOME", output / "home"),
                          ("XDG_CONFIG_HOME", output / "config")):
        if os.environ.get(key) != str(expected):
            raise RuntimeError("Capture requires its private session environment")
    kwin = background = vm = None
    effect = os.environ.get("MTTKDE_CAPTURE_EFFECT", "liquidglass")
    script = str(Path(__file__).resolve())

    def dbus(*args):
        return subprocess.run(["qdbus6", "org.kde.KWin", *args],
                              capture_output=True, text=True, check=True, timeout=10).stdout.strip()

    def capture(name):
        time.sleep(1)
        capture_env = env.copy()
        capture_env["QT_QPA_PLATFORM"] = "wayland"
        with (output / "spectacle.log").open("a") as log:
            subprocess.run(["spectacle", "--background", "--nonotify", "--fullscreen",
                            "--output", str(output / name)], env=capture_env, check=True,
                           timeout=15, stdout=log, stderr=subprocess.STDOUT)
        assert (output / name).is_file(), "Screenshot failed"

    try:
        with (output / "kwin.log").open("w") as log:
            kwin = subprocess.Popen([
                str(output / "bin/kwin_wayland"), "--virtual",
                *(["--xwayland"] if os.environ["MTTKDE_CAPTURE_BACKEND"] == "xcb" else []),
                "--scale", os.environ["MTTKDE_CAPTURE_SCALE"],
                "--width", "960", "--height", "640", "--no-lockscreen",
                "--no-global-shortcuts", "--no-kactivities",
                "--exit-with-session", shlex.join([sys.executable, script, "--session"]),
            ], stdout=log, stderr=subprocess.STDOUT)
        wait_for(lambda: (output / "session-env.json").exists())
        assert_compositor_owner(kwin.pid)
        env = json.loads((output / "session-env.json").read_text())
        env["QT_QPA_PLATFORM"] = "wayland"
        # The virtual backend's --scale can change pixel dimensions while
        # leaving the output at 1x. Set and verify the actual compositor scale.
        scale = float(os.environ["MTTKDE_CAPTURE_SCALE"])
        subprocess.run(["kscreen-doctor", f"output.Virtual-0.scale.{scale:g}"],
                       env=env, check=True, timeout=10, stdout=subprocess.DEVNULL)
        outputs = json.loads(subprocess.check_output(
            ["kscreen-doctor", "-j"], env=env, text=True, timeout=10))["outputs"]
        assert any(output["name"] == "Virtual-0" and output["scale"] == scale
                   for output in outputs), "Virtual output scale was not applied"
        with (output / "clients.log").open("w") as log:
            if not os.environ.get("MTTKDE_CAPTURE_DESKTOP"):
                background = subprocess.Popen([sys.executable, script, "--client", "desktop",
                                               "-name", "capture-desktop"], env=env,
                                              stdout=log, stderr=subprocess.STDOUT)
            time.sleep(1)
            vm_env = env | {"QT_QPA_PLATFORM": os.environ["MTTKDE_CAPTURE_BACKEND"]}
            vm = subprocess.Popen([sys.executable, script, "--client", "vm", "-name", os.environ["MTTKDE_CAPTURE_IDENTITY"]],
                                  env=vm_env, stdout=log, stderr=subprocess.STDOUT)
        time.sleep(1)
        dbus("/Effects", "org.kde.kwin.Effects.unloadEffect", effect)
        capture("effect-off.png")
        loaded = dbus("/Effects", "org.kde.kwin.Effects.loadEffect", effect)
        active = dbus("/Effects", "org.kde.kwin.Effects.activeEffects")
        (output / "support.txt").write_text(dbus("/KWin", "org.kde.KWin.supportInformation"))
        (output / "effects.txt").write_text(dbus("/Effects", "org.kde.kwin.Effects.listOfEffects"))
        plugin_loads = [line for line in (output / "kwin.log").read_text().splitlines()
                       if f"{effect}.so" in line and '" loaded library' in line]
        plugin = output / f"plugins/kwin/effects/plugins/{effect}.so"
        mappings = [line for line in Path(f"/proc/{kwin.pid}/maps").read_text().splitlines()
                    if f"/{effect}.so" in line]
        assert mappings and all(
            line.split(maxsplit=5)[5] == str(plugin)
            and int(line.split()[4]) == plugin.stat().st_ino for line in mappings
        ), "KWin must map this probe's exact plugin inode"
        (output / "evidence.json").write_text(json.dumps({
            "loaded": loaded, "active_effects": active, "plugin_loads": plugin_loads,
            "plugin_mappings": mappings,
            "dbus_owner_verified": True, "kwin_pid": kwin.pid,
            "identity": os.environ["MTTKDE_CAPTURE_IDENTITY"],
            "client_backend": os.environ["MTTKDE_CAPTURE_BACKEND"], "scale": os.environ["MTTKDE_CAPTURE_SCALE"],
            "plugin_sha256": hashlib.sha256((output / f"plugins/kwin/effects/plugins/{effect}.so").read_bytes()).hexdigest(),
            "kwin_version": subprocess.check_output(
                [str(output / "bin/kwin_wayland"), "--version"], text=True, timeout=5).strip(),
        }, indent=2))
        assert loaded == "true" and effect in active.splitlines(), "Effect did not activate"
        assert vm.poll() is None and (background is None or background.poll() is None), "Test client exited"
        capture("effect-on.png")
        if os.environ.get("MTTKDE_CAPTURE_COMPANION"):
            assert dbus("/Effects", "org.kde.kwin.Effects.loadEffect", "liquidglass") == "true"
            assert "liquidglass" in dbus("/Effects", "org.kde.kwin.Effects.activeEffects").splitlines()
            companion = output / "plugins/kwin/effects/plugins/liquidglass.so"
            mappings = [line for line in Path(f"/proc/{kwin.pid}/maps").read_text().splitlines()
                        if "/liquidglass.so" in line]
            assert mappings and all(line.split(maxsplit=5)[5] == str(companion)
                                    and int(line.split()[4]) == companion.stat().st_ino for line in mappings)
            (output / "companion.json").write_text(json.dumps({
                "plugin_mappings": mappings, "sha256": hashlib.sha256(companion.read_bytes()).hexdigest(),
                "active": True}, indent=2))
            capture("combined.png")
            dbus("/Effects", "org.kde.kwin.Effects.unloadEffect", "liquidglass")
            capture("restored.png")
    finally:
        stop(vm)
        stop(background)
        stop(kwin)


def run(plugin, output, scale, expected, backend, identity, renderer="software", shader_dir=None, companion=None, desktop_surface=False, squircle_blend=0.0, refraction_pattern=False):
    effect = "kwin4_effect_shapecorners" if shader_dir else "liquidglass"
    output.mkdir(parents=True, exist_ok=False)
    for subdir in ("home", "config", "data", "cache"):
        (output / subdir).mkdir(mode=0o700)
    (output / "bin").mkdir()
    # copyfile does not carry the system binary's cap_sys_nice xattr.
    # Qt can then honor this private QT_PLUGIN_PATH without privileges.
    kwin_copy = output / "bin/kwin_wayland"
    shutil.copyfile(shutil.which("kwin_wayland"), kwin_copy)
    kwin_copy.chmod(0o755)
    dest = output / f"plugins/kwin/effects/plugins/{effect}.so"
    dest.parent.mkdir(parents=True)
    shutil.copy2(plugin, dest)
    if companion:
        assert shader_dir, "The companion probe requires Rounded Corners"
        shutil.copy2(companion, dest.parent / "liquidglass.so")
    if shader_dir:
        shaders = output / "data/kwin/shaders"
        shaders.mkdir(parents=True)
        for name in ("shapecorners.frag", "shapecorners_core.frag"):
            shutil.copyfile(shader_dir / name, shaders / name)
    (output / "config/kwinrc").write_text(
        "[Compositing]\nBackend=OpenGL\n[Plugins]\nliquidglassEnabled=false\n"
        "blurEnabled=false\nkwin4_effect_shapecornersEnabled=false\n"
        "[Effect-liquidglass]\nBlurStrength=3.5\nBlurDecorations=true\n"
        "BlurMatching=false\nNoiseStrength=0\nWindowCornerRadius=22\n")
    if shader_dir:
        with (output / "config/kwinrc").open("a") as config:
            config.write(
                "[Windows]\nPlacement=Centered\n"
                "[org.kde.kdecoration2]\nBorderSize=None\nBorderSizeAuto=false\n"
                "[Round-Corners]\nSize=28\nInactiveCornerRadius=28\n"
                "UseSquircleShape=false\nUseNativeDecorationShadows=false\n"
                "AnimationDuration=0\nOutlineThickness=3\nInactiveOutlineThickness=3\n"
                "OutlineColor=255,0,0\nInactiveOutlineColor=255,0,0\n"
                "ActiveOutlineUsePalette=false\nInactiveOutlineUsePalette=false\n"
                "ActiveOutlineUseCustom=true\nInactiveOutlineUseCustom=true\n"
                "SecondOutlineThickness=0\nInactiveSecondOutlineThickness=0\n")
    if squircle_blend:
        assert shader_dir and 0.0 <= squircle_blend <= 1.0
        with (output / "config/kwinrc").open("a") as config:
            config.write(f"[Round-Corners]\nUseSquircleShape=true\nSquircleness={squircle_blend}\n")
    if desktop_surface:
        assert backend == "xcb" and shader_dir and not companion
        with (output / "config/kwinrc").open("a") as config:
            config.write("[Round-Corners]\nInclusions=" + identity + "\n")
    if companion:
        with (output / "config/kwinrc").open("a") as config:
            config.write("[Effect-liquidglass]\nNoiseStrength=16\n"
                         "[Round-Corners]\nOutlineThickness=0\nInactiveOutlineThickness=0\n"
                         "ShadowSize=0\nInactiveShadowSize=0\n")
    env = {key: value for key, value in os.environ.items()
           if key in ("PATH", "LANG", "LC_ALL", "USER", "LOGNAME")}
    # UNIX sockets have a 108-byte path limit; repository paths may be longer.
    runtime = tempfile.TemporaryDirectory(prefix="mttcap-")
    env.update(HOME=str(output / "home"), XDG_CONFIG_HOME=str(output / "config"),
               XDG_DATA_HOME=str(output / "data"), XDG_CACHE_HOME=str(output / "cache"),
               XDG_RUNTIME_DIR=runtime.name, QT_PLUGIN_PATH=str(output / "plugins"),
               QT_QPA_PLATFORM="offscreen", QT_DEBUG_PLUGINS="1", XCURSOR_SIZE="24",
               QT_FORCE_STDERR_LOGGING="1", QT_LOGGING_RULES="kwin_*.debug=true;qt.core.plugin.*.debug=true",
               LIBGL_ALWAYS_SOFTWARE="1" if renderer == "software" else "0", KWIN_COMPOSE="O2",
               MTTKDE_CAPTURE_DIR=str(output), MTTKDE_CAPTURE_SCALE=str(scale),
               MTTKDE_CAPTURE_BACKEND=backend, MTTKDE_CAPTURE_IDENTITY=identity,
               MTTKDE_CAPTURE_DESKTOP="1" if desktop_surface else "", MTTKDE_CAPTURE_EFFECT=effect,
               MTTKDE_CAPTURE_COMPANION="1" if companion else "",
               MTTKDE_CAPTURE_REFRACTION_PATTERN="1" if refraction_pattern else "")
    command = ["dbus-run-session", "--", sys.executable, str(Path(__file__).resolve()),
               "--inside", str(output)]
    # Screenshot authorization on older KWin uses the desktop-entry cache.
    # Build it in this probe's private HOME/cache, never the user's session.
    if shutil.which("kbuildsycoca6"):
        menus = output / "config/menus"
        menus.mkdir()
        (menus / "applications.menu").write_text(
            '<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN" '
            '"http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">'
            '<Menu><Name>Applications</Name><DefaultAppDirs/>'
            '<Include><All/></Include></Menu>')
        with (output / "sycoca.log").open("w") as log:
            subprocess.run(["kbuildsycoca6", "--noincremental"], env=env,
                           check=True, timeout=30, stdout=log, stderr=subprocess.STDOUT)
    process = subprocess.Popen(command, env=env, start_new_session=True)
    try:
        if process.wait(timeout=60):
            raise RuntimeError("Isolated compositor capture failed; inspect logs")
    finally:
        # Kill only this invocation's private process group, also on timeout.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        stop(process)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        runtime.cleanup()
    if desktop_surface:
        from PIL import Image, ImageChops
        original = Image.open(output / "effect-off.png").convert("RGB")
        rendered = Image.open(output / "effect-on.png").convert("RGB")
        assert original.getcolors(original.width * original.height) and sum(
            count for count, color in original.getcolors(original.width * original.height)
            if color == (55, 120, 170)) > 30000, "Desktop surface missing"
        passed = ImageChops.difference(original, rendered).getbbox() is None
        (output / "pixels.json").write_text(json.dumps({"desktop_unchanged": passed}) + "\n")
        assert passed, "ShapeCorners changed a desktop surface"
    elif companion:
        compare_corners(output)
    elif shader_dir:
        compare_outline(output)
    else:
        compare(output, expected)


def compare_corners(output):
    """Glass and grain must not fill the pixels removed by ShapeCorners."""
    from PIL import Image
    images = [Image.open(output / name).convert("RGB") for name in
              ("effect-off.png", "effect-on.png", "combined.png", "restored.png")]
    original, rounded, combined, restored = images
    blue = (55, 120, 170)
    background = {(33, 66, 99), (225, 199, 135)}
    cutouts = [(x, y) for y in range(original.height) for x in range(original.width)
               if original.getpixel((x, y)) == blue and rounded.getpixel((x, y)) in background]
    assert len(cutouts) > 20, "Rounded corner cutouts were not visible"
    changed = sum(combined.getpixel(p) != rounded.getpixel(p) for p in cutouts)
    assert all(restored.getpixel(p) == rounded.getpixel(p) for p in cutouts), "Unload did not restore corners"
    body = [(x, y) for y in range(original.height) for x in range(original.width)
            if original.getpixel((x, y)) == blue]
    left, right = min(x for x, y in body), max(x for x, y in body)
    top, bottom = min(y for x, y in body), max(y for x, y in body)
    center_changes = sum(combined.getpixel((x, y)) != rounded.getpixel((x, y))
                         for y in range(top + (bottom-top)//3, top + 2*(bottom-top)//3)
                         for x in range(left + (right-left)//3, left + 2*(right-left)//3))
    assert center_changes > 100, "Glass was not visibly rendered inside the translucent client"
    metrics = {"cutout_pixels": len(cutouts), "leaked_pixels": changed,
               "interior_changed_pixels": center_changes, "passed": changed == 0}
    (output / "pixels.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics))
    assert metrics["passed"], "Glass or grain leaked outside the rounded window"


def compare_outline(output):
    from PIL import Image

    def bounds(path, matches):
        with Image.open(path).convert("RGB") as image:
            points = [(x, y) for y in range(image.height) for x in range(image.width)
                      if matches(image.getpixel((x, y)))]
        assert points, f"Test surface or outline missing in {path}"
        return (min(x for x, y in points), min(y for x, y in points),
                max(x for x, y in points), max(y for x, y in points))

    client = bounds(output / "effect-off.png", lambda p: p == (55, 120, 170))
    outline = bounds(output / "effect-on.png", lambda p: p[0] > 230 and p[1] < 20 and p[2] < 20)
    assert client[2] - client[0] > 400, "Test window is not mapped at its expected size"
    delta = outline[3] - client[3]
    metrics = {"client_bounds": client, "outline_bounds": outline,
               "bottom_offset": delta, "passed": abs(delta) <= 4}
    (output / "pixels.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics))
    assert metrics["passed"], "Rounded outline is displaced from the window bottom"


def compare(output, expected):
    from collections import Counter
    from PIL import Image, ImageChops

    with Image.open(output / "effect-off.png") as image:
        baseline = image.convert("RGB")
    with Image.open(output / "effect-on.png") as image:
        rendered = image.convert("RGB")
    assert baseline.size == rendered.size
    area = baseline.width * baseline.height

    def pixels(image):
        # Avoid Pillow's deprecated getdata while supporting older distros.
        channel = iter(image.tobytes())
        return zip(channel, channel, channel)

    histogram = Counter(pixels(baseline))
    # Reject blank captures or an unmapped guest/background before comparing.
    assert histogram[(55, 120, 170)] > area / 12, "Guest rectangle missing"
    assert histogram[(33, 66, 99)] > area / 4, "Dark background tiles missing"
    assert histogram[(225, 199, 135)] > area / 4, "Light background tiles missing"
    difference = ImageChops.difference(baseline, rendered)
    changed = sum(pixel != (0, 0, 0) for pixel in pixels(difference))
    passed = changed == 0 if expected == "unchanged" else changed > area / 2
    metrics = {"expected": expected, "changed_pixels": changed,
               "total_pixels": area, "passed": passed}
    (output / "pixels.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics))
    assert passed, "Pixel comparison failed"


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scale", type=float, choices=(1, 1.25, 1.5, 1.75, 2), default=1)
    parser.add_argument("--identity", default="VirtualBoxVM")
    parser.add_argument("--backend", choices=("wayland", "xcb"), default="wayland")
    parser.add_argument("--renderer", choices=("software", "hardware"), default="software")
    parser.add_argument("--expect", choices=("unchanged", "changed"), default="unchanged")
    parser.add_argument("--rounded-shaders", type=Path, help="Test Rounded Corners using these built shaders")
    parser.add_argument("--squircle-blend", type=float, choices=(0.0, 0.55, 1.0), default=0.0)
    parser.add_argument("--desktop-surface", action="store_true", help="Probe an Xwayland desktop window, including forced inclusions")
    parser.add_argument("--companion-plugin", type=Path, help="Also test Acrylic Glass with Rounded Corners")
    parser.add_argument("--refraction-pattern", action="store_true", help="Use diagonal lines over color bands behind the test window")
    parser.add_argument("--inside", type=Path)
    parser.add_argument("--session", action="store_true")
    parser.add_argument("--client", choices=("desktop", "vm"))
    args, _qt_args = parser.parse_known_args()
    if args.client:
        client(args.client)
    elif args.session:
        session()
    elif args.inside:
        inside(args.inside)
    elif args.plugin and args.output:
        run(args.plugin.resolve(), args.output.resolve(), args.scale, args.expect, args.backend, args.identity, args.renderer,
            args.rounded_shaders.resolve() if args.rounded_shaders else None,
            args.companion_plugin.resolve() if args.companion_plugin else None, args.desktop_surface,
            args.squircle_blend, args.refraction_pattern)
    else:
        parser.error("--plugin and --output required")
