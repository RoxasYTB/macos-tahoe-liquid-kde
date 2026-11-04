"""Exercise the production blur gate with synthetic KWin window metadata."""

import shlex
import shutil
import subprocess

import pytest


@pytest.fixture(scope="module")
def blur_gate(tmp_path_factory):
    from pathlib import Path

    if not shutil.which("c++") or not shutil.which("pkg-config"):
        pytest.skip("C++ compiler and Qt6Core development files required")
    flags = subprocess.run(["pkg-config", "--cflags", "--libs", "Qt6Core"],
                           capture_output=True, text=True, timeout=10)
    if flags.returncode:
        pytest.skip("Qt6Core development files required")
    source = (Path(__file__).resolve().parents[1] /
              "src/offline/kwin-effects/acrylic-glass/src/effect.cpp").read_text()
    method = source.split("bool BlurEffect::shouldBlur(", 1)[1].split("\n}\n", 1)[0]
    work = tmp_path_factory.mktemp("acrylic-filter")
    harness = work / "gate.cpp"
    harness.write_text(r'''
#include <QString>
#include <QStringList>
#include <QVariant>
#include <QtGlobal>
#include <iostream>
constexpr int WindowForceBlurRole = 1, PAINT_WINDOW_TRANSFORMED = 2;
constexpr int OverlayLayer = 3, ActiveLayer = 4;
struct Window {
    QString cls, name;
    QString resourceClass() const { return cls; }
    QString resourceName() const { return name; }
    int layer() const { return 0; }
};
struct EffectWindow {
    Window meta;
    bool moving = false;
    bool resizing = false;
    bool forced = true;
    bool isDesktop() const { return false; }
    bool isUserMove() const { return moving; }
    bool isUserResize() const { return resizing; }
    QVariant data(int) const { return forced; }
    const Window *window() const { return &meta; }
};
struct WindowPaintData {
    double xScale() const { return 1; }
    double yScale() const { return 1; }
    double xTranslation() const { return 0; }
    double yTranslation() const { return 0; }
};
struct Effects {
    bool activeFullScreenEffect() const { return false; }
} handler;
auto effects = &handler;
struct BlurEffect {
    bool m_whitelist;
    QStringList m_windowClasses;
    bool m_blurDuringMoveResize;
    bool shouldBlur(const EffectWindow *, int, const WindowPaintData &) const;
};
''' + "bool BlurEffect::shouldBlur(" + method + "\n}\n" + r'''
int main(int argc, char **argv) {
    if (argc != 9) return 2;
    EffectWindow window{{QString::fromUtf8(argv[1]), QString::fromUtf8(argv[2])}};
    window.moving = QString::fromUtf8(argv[5]) == "1";
    window.resizing = QString::fromUtf8(argv[6]) == "1";
    window.forced = QString::fromUtf8(argv[8]) == "1";
    BlurEffect effect{QString::fromUtf8(argv[3]) == "whitelist",
                      QString::fromUtf8(argv[4]).split(','),
                      QString::fromUtf8(argv[7]) == "1"};
    std::cout << effect.shouldBlur(&window, 0, WindowPaintData{});
}
''')
    binary = work / "gate"
    subprocess.run(["c++", "-std=c++17", "-fPIC", str(harness), "-o", str(binary),
                    *shlex.split(flags.stdout)], check=True, capture_output=True, timeout=60)
    return binary


@pytest.mark.parametrize("cls,name,mode,entries,moving,resizing,allow_motion,forced,expected", [
    ("VirtualBoxVM", "VirtualBoxVM", "blacklist", "", "0", "0", "0", "1", "0"),
    ("VirtualBoxVM", "guest", "blacklist", "custom-app", "0", "0", "0", "1", "0"),
    ("guest", "VirtualBoxVM", "blacklist", "custom-app", "0", "0", "0", "1", "0"),
    ("virtualboxvm", "guest", "blacklist", "", "0", "0", "0", "1", "0"),
    ("guest", "VIRTUALBOXVM", "blacklist", "", "0", "0", "0", "1", "0"),
    ("VirtualBoxVM", "guest", "whitelist", "VirtualBoxVM", "0", "0", "0", "1", "0"),
    ("guest", "VirtualBoxVM", "whitelist", "guest", "0", "0", "0", "1", "0"),
    ("VirtualBox", "VirtualBox", "blacklist", "", "0", "0", "0", "1", "1"),
    ("VirtualBox Manager", "VirtualBox", "blacklist", "", "0", "0", "0", "1", "1"),
    ("org.kde.dolphin", "dolphin", "blacklist", "custom-app", "0", "0", "0", "1", "1"),
    ("custom-app", "custom-app", "blacklist", "custom-app", "0", "0", "0", "1", "0"),
    ("custom-app", "custom-app", "whitelist", "custom-app", "0", "0", "0", "1", "1"),
    ("org.kde.dolphin", "dolphin", "whitelist", "custom-app", "0", "0", "0", "1", "0"),
    ("plasmashell", "plasmashell", "whitelist", "plasmashell,tahoe-control-center", "0", "0", "0", "1", "1"),
    ("tahoe-control-center", "tahoe-control-center", "whitelist", "plasmashell,tahoe-control-center", "0", "0", "0", "1", "1"),
    ("google-chrome", "google-chrome", "whitelist", "plasmashell,tahoe-control-center", "0", "0", "0", "1", "0"),
    ("org.kde.dolphin", "dolphin", "blacklist", "custom-app", "1", "0", "0", "0", "0"),
    ("org.kde.dolphin", "dolphin", "blacklist", "custom-app", "0", "1", "0", "0", "0"),
    ("org.kde.dolphin", "dolphin", "blacklist", "custom-app", "1", "0", "1", "0", "1"),
    ("org.kde.dolphin", "dolphin", "blacklist", "custom-app", "1", "0", "0", "1", "1"),
])
def test_vm_surfaces_skip_glass_without_changing_other_filters(
        blur_gate, cls, name, mode, entries, moving, resizing, allow_motion, forced, expected):
    result = subprocess.run([str(blur_gate), cls, name, mode, entries,
                             moving, resizing, allow_motion, forced],
                            capture_output=True, text=True, check=True, timeout=5)
    assert result.stdout == expected


def test_interactive_move_skips_translucent_prepaint_work():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] /
              "src/offline/kwin-effects/acrylic-glass/src/effect.cpp").read_text()
    start = source.index("void BlurEffect::prePaintWindow(")
    end = source.index("bool BlurEffect::shouldBlur(", start)
    prepaint = source[start:end]
    motion_guard = (
        "if (!m_blurDuringMoveResize && (w->isUserMove() || w->isUserResize())"
    )
    assert motion_guard in prepaint
    assert prepaint.index(motion_guard) < prepaint.index("const Region blurArea")
