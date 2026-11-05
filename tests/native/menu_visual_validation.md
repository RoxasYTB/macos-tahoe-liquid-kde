# Popup rendering validation

## v0.56.3 follow-up — 2026-10-20

Menu and tooltip blur radii now match Kvantum's drawn SVG corners (9 and 6
logical pixels). Plasma dialog, tooltip and Dock masks use their visible
surface paths. Acrylic Glass fits the client region, including inset shadow
margins and square surfaces, and antialiases menus, tooltips and panels as well
as applet popups. Custom cutouts and Rounded Corners' runtime shape remain
protected. Real KSvg masks pass at 100%, 125%, 150%, 175% and 200%.

The Dock fill is 4% and every material excludes it from the gradient. Golden
Gate starts with 95% black tint, fades to zero at half-height and leaves the
lower half untinted. Tahoe stays untinted. The actual legacy and core shaders
pass black/white backdrop, gradient extent and premultiplied coverage checks.
Blur and restrained color refraction are increased without adding opaque fills.

The full suite reported 1462 passed, 3 skipped and one stale README test-count
badge failure; that badge was corrected and its check rerun successfully.
The final 50% gradient passed all 16 material tests. Both effect and KCM build
against the host 6.7 SDK and isolated 6.6/6.8 SDK containers.
The focused final compositor probe captures context menus, submenus, tooltips
and Plasma popups at 150%, with effects on/off. Publication screenshots use a
separate disposable KDE neon VM and the verified running plugin identity.
Checks were deliberately limited after the requested final gradient adjustment;
this is not a new exhaustive application or driver qualification.

## Earlier validation

2026-10-17, following the #77/#89 corner and desktop fixes in `bc0d3c4`.
The repository also received independent VM/OLED commits during this work;
this follow-up changes popup rendering, assets and the isolated test tools.

## Changes verified

- KWin 6.7 removed `EffectWindow::readProperty()` from its Wayland SDK.
  Acrylic Glass consequently ignored Xwayland's blur property. Reading the
  bounded XCB property directly restores those client-requested regions on
  6.6–6.8. Missing, malformed, truncated and overflowing requests never become
  implicit full-window blur. Tooltips also skip the normal-decoration fallback.
- The light Kvantum menu multiplied SVG opacity 0.6 by the configured 0.55
  opacity, while dark used 1.0 × 0.55. Interior and frame surface fills now use
  the same effective opacity in both modes. Shadow gradients, highlights and
  cutouts remain intact. Light tooltip shadow depth now matches dark (6).
- Three bundled GTK4 light stylesheets contained six invalid `color-mix()`
  expressions each. Missing commas are fixed in the active sheet and both
  copies. GTK's actual CSS parser accepts every bundled GTK4 stylesheet.
- Reduced-transparency variants are generated from these corrected sources;
  no live theme or user's radius configuration was rewritten.

## Automated and native checks

`MTTKDE_ROUNDED_CORNERS_ARCHIVE=/tmp/issue100-rounded.tar.gz ./test --slow -q`:
**1442 passed**, including the verified Rounded Corners source build.
The three added tests render menu SVG elements with QSvgRenderer, parse GTK4
CSS with Gtk.CssProvider, and compile the production XCB property-reading block
against a private Xvfb server. The latter exercises absent/empty/valid regions,
wrong types, malformed tuples, oversized replies and integer overflow.

Acrylic Glass and its KCM built against the host KWin 6.7.4 SDK and isolated,
network-disabled 6.6.4 and 6.8.0 SDK containers. These are compilation checks;
they do not establish all-distro or all-driver runtime qualification.
The native pointer and KSvg helpers built through `tests/native/CMakeLists.txt`.
The pointer helper rejected input when the private D-Bus compositor PID did
not match, before opening a Wayland connection.

## Visual checks

The private compositor loaded the exact staged effect binaries (mapped path
and inode verified), with the installer's real Acrylic preset and Rounded
Corners radius 28. Assets, home, configuration, cache and D-Bus were private.
The host desktop was neither installed into nor restarted.

| Capture directory under `build/` | Cases |
| --- | ---: |
| `menu-final-light-v2` | 10 Wayland, light |
| `menu-qualified-dark` | 10 Wayland, dark |
| `menu-qualified-reduced-light` | 10 reduced transparency, light |
| `menu-qualified-reduced-dark` | 10 reduced transparency, dark |
| `menu-verified-xcb` | 10 Xwayland, light |
| `menu-verified-xcb-dark` | 10 Xwayland, dark |
| `menu-verified-scale125` | 8 Wayland at 125% |

The ten families are menu-bar dropdown, context menu, submenu, combo popup,
tooltip, dialog, Plasma Dialog, GTK3 menu, GTK3 popover and GTK4 popover. The
fractional-scale set omits the menu-bar dropdown and dialog. Each successful
case has `on.png` and `off.png`: **68 cases / 136 screenshots**. Four KSvg
atlases cover five frame families each, in light/dark and standard/reduced
transparency: **20 frames**. `build/menu-review/index.html` links the final
captures; `summary.png` provides a contact sheet. These local artifacts are
intentionally not committed. Instructions to reproduce are in CONTRIBUTING.md.

A pre-fix Xwayland control (`menu-control-xcb`, plugin from `bc0d3c4`) had
**0 / 31616** menu-interior pixels change by more than 8 RGB levels when
switching effects on. The fixed capture (`menu-verified-xcb/context`) had
**2063 / 31616** change, with visibly blurred underlying text. The same menu
geometry and preset were used. The prior #89 cutout/noise and desktop-eligibility
controls remain covered by `test_corner_rendering.py` and the combined-effect
capture probe.

## Real Plasma desktop menu — 2026-11-04

The installed Plasma Folder View context menu was opened in a private Xorg
dummy display (`:162`) with private HOME/XDG, D-Bus, KWin X11 and Plasma. The
menu and its real `Create New` submenu were captured at
`/tmp/tahoe-plasma-menu-submenu-20261104/desktop-context-menu.png` and
`desktop-context-menu-submenu.png`; the hovered parent row is in
`desktop-context-menu-hover.png`. KWin's `/Effects` API reported
`liquidglass` active, and `/proc/<kwin-pid>/maps` confirmed the private plugin
copy. The submenu screenshot keeps the live wallpaper visible through both
surfaces. This checks the real action/submenu path and compositor integration
for the installed dark profile; it does not claim light-profile parity or
keyboard traversal. The active desktop session was not touched.

The menu was recaptured at the reference position `(1000, 327)` on the same
1920 × 1080 wallpaper. A private three-way crop is available at
`/tmp/tahoe-plasma-menu-aligned-20261104/desktop-context-menu-aligned-comparison.png`
(macOS reference, current KDE with 13 px frame margins, and a private 0 px
margin experiment). The 0 px experiment loses the rounded outer shape, so the
existing 13 px local setting is retained. With 13 px, the rounded outer frame
is visible but the row field remains inset and rectangular; that is the next
surface integration issue to address. Neither experiment changed the local
Kvantum config or the user's desktop.

A separate private test set `[Menu] interior.element=none` while keeping the
13 px frame margins. It removed the inset rectangular fill in the real Plasma
capture, but failed `test_native_qt_menu_text_contrasts_with_each_theme` in the
dark profile: 0 sampled pixels reached 4.5:1 contrast. That option was
discarded and the source configs retain `interior.element=menu`. A replacement
needs a rounded interior surface that still passes the native text contrast
check.

## Rounded menu surface follow-up — 2026-11-05

The earlier 0 px margin experiment above used the then-square inner patch and
did lose the rounded outer edge. The later paired change rounded the SVG
`menu-normal` patch in both profiles and then set `[Menu]` frame margins to 0;
that combination was captured through the real desktop containment menu and
removed the visible inset card. Source checkpoint: `e3ae64a`.

Fresh private Xorg/KWin captures after that source change:

| Profile | Rest | Hover | Submenu | Glass-off comparison |
| --- | --- | --- | --- | --- |
| Dark | `/tmp/tahoe-plasma-menu-source-final-20261105/desktop-context-menu.png` | `.../desktop-context-menu-hover.png` | `.../desktop-context-menu-submenu.png` | `.../desktop-context-menu-glass-off.png` |
| Light | `/tmp/tahoe-plasma-menu-light-source-20261105/desktop-context-menu.png` | `.../desktop-context-menu-hover.png` | `.../desktop-context-menu-submenu.png` | `.../desktop-context-menu-glass-off.png` |

Both runs use the installed desktop Folder View action path, private HOME/XDG
and D-Bus, and the private KWin X11 display. KWin's active-effect list includes
`liquidglass` and `kwin4_effect_shapecorners`; its process map points to the
private effect copy and Plasma's map contains `libkvantum.so`. The light capture
also includes `desktop-context-menu-keyboard-focus.png`; it demonstrates a
keyboard selection state but does not verify the full keyboard traversal.
The dark root surface is close to the reference's floating plum glass. The
light profile remains visibly too pale and its corner treatment reads tighter
than the reference. KDE's native labels and available actions remain intact;
they do not match Finder's wording. A targeted black-purple fill/white-text
experiment was discarded because the native Qt contrast check failed; source
files remain at checkpoint `e3ae64a`. No active Plasma/KWin session was
changed.

## Light menu tint correction — 2026-11-05

The previous dark-fill experiment used the original 0.38 surface alpha and
failed the 4.5:1 native Qt menu contrast check. The follow-up keeps the light
profile's rounded geometry and edge treatment, changes only the center and
matching corner fill to `#14031a` at 0.50 opacity, and sets the light menu/menu
item foreground to white. This keeps the menu translucent while producing the
deeper plum surface in the reference. The native contrast check now passes.

Fresh real desktop-menu render, with the source light Kvantum assets and the
private Xorg/KWin session described above:
`/tmp/tahoe-plasma-menu-light-source-20261105/desktop-context-menu.png`.
The same directory contains hover, submenu, keyboard-selection and glass-off
captures. `liquidglass` and `kwin4_effect_shapecorners` were active in that
private KWin; Plasma mapped Kvantum. The target menu's contrast and color are
closer to macOS, though its panel proportions still follow KDE's longer native
action labels and the corners are somewhat tighter than the reference.

`python3 -m pytest -q tests/test_menu_rounding.py tests/test_popup_rendering.py
--tb=short`: **9 passed, 3 skipped** (PyQt6.QtSvg unavailable). `git diff
--check` is clean. The active desktop and its color scheme were not changed.

## Isolated outer-rim diagnosis — 2026-11-05

A private Light-profile Plasma render changed only the `menu-normal` center
path to a 12 px corner radius; all repository assets remained untouched. In
`/tmp/tahoe-plasma-menu-radius-trial-20261105/desktop-context-menu.png`, the
center fill develops a pronounced inset arc, while the bright rectangular
outer perimeter remains unchanged. This rules out the center fill path as the
source of that perimeter. The experiment was discarded. Further work should
trace the QMenu frame/rim element independently before changing the theme; do
not keep increasing `menu-normal` rounding. The current real Plasma menu,
KDE action list and submenu still work in the isolated render; no active
desktop settings were changed.

Follow-up isolated source/config comparison found both checked-in Kvantum
profiles currently use `[Menu] frame.*=0`, despite an older plan note about a
local 13 px value. Overriding all four margins to 13 in a private Light-profile
Plasma run restores a clear rounded outer silhouette, but produces an overly
wide pale rim (`/tmp/tahoe-plasma-menu-margin13-current-20261105/desktop-context-menu.png`).
A single 3 px variant retains a pale thin frame with tighter corners
(`/tmp/tahoe-plasma-menu-margin3-current-20261105/desktop-context-menu.png`).
Neither temporary setting is accepted. The source stays unchanged until the
frame fill/highlight can be separated from its rounding; correct the stale
plan note before any future margin edits.

### Isolated light-frame trials before the paired correction — 2026-11-05

The current Light-profile render at 0 px still has a hard bright perimeter
and corners tighter than the macOS reference. One private Xorg/KWin trial set
all four `[Menu] frame.*` margins to 13 and reduced the white highlight alpha
inside the `menu-normal` nine-patch from 0.22 to 0.07. The result
(`/tmp/tahoe-plasma-menu-radius-muted-20261105/desktop-context-menu.png`)
rounds the panel but retains a thick pale frame; reducing the SVG highlight
did not control that frame. The experiment used a temporary XDG tree and
private KWin, and ended with the harness. No repository theme asset or active
desktop setting changed. Do not repeat this SVG-only highlight adjustment;
the remaining edge is not controlled by that SVG highlight.

A second isolated trial set `[Menu] frame=false` and increased only the
`menu-normal` center patch corner radius to 10 px. The pale frame disappeared,
but the menu fill developed asymmetric rounded corners
(`/tmp/tahoe-plasma-menu-interior-round-20261105/desktop-context-menu.png`).
This rejects a center-path-only fix: the frame and the four interior corner
patches need to be changed together. Both trials used temporary XDG trees and
private Xorg/KWin sessions; neither changed repository assets or the active
desktop. The paired correction below supersedes the earlier “edit the complete
nine-patch” next step.

### Rounded menu fill checkpoint — 2026-11-05

Tracing the upstream Kvantum Qt 6 `PE_PanelMenu` paint path showed why
`frame.*=0` retained a visible rim: zero frame margins do not disable the
inherited `hasFrame` flag. The style paints the interior and then the frame as
separate elements. Setting `[Menu] frame=false` removes that extra frame; a
thin dark stroke on each profile's existing translucent `menu-normal` path
provides the edge without a second filled band.

This paired change is rendered through the actual Plasma desktop Folder View
menu in private Xorg/KWin sessions: Light at
`/tmp/tahoe-plasma-menu-interior-stroke-valid-20261105/desktop-context-menu.png`
and Dark at
`/tmp/tahoe-plasma-menu-dark-rounded-fill-20261105/desktop-context-menu.png`.
The existing native KDE actions and submenu remain in the menu. The Light
capture is closer to the reference's floating rounded silhouette; both
profiles retain live wallpaper visibility behind the translucent surface.
`python3 -m pytest -q tests/test_menu_rounding.py tests/test_popup_rendering.py
--tb=short` reports **9 passed, 3 skipped** (PyQt6.QtSvg unavailable); XML
parsing of both SVGs and `git diff --check` pass. These are isolated-session
checks; the active Plasma/KWin session was not changed. Residual differences
include KDE's native action labels and the resulting wider/taller proportions.

## Limits and probe corrections

These are toolkit-family and frame checks, not an assertion that every external
application or complete Plasma applet workflow has been exercised. They do not
reproduce the original NVIDIA/Plasma edit-mode report in #77.

A Wayland trace showed KWindowSystem discovering blur capability after the
menu's first surface commit and sending a region without another immediate
commit. The probe requests a second paint before the final screenshot. It
therefore measures settled rendering; it does not claim to repair that
external client's first-frame scheduling.

Exploratory Xwayland combo/tooltip runs initially failed the probe's visibility
assertions. GDB localized the abort to an unhandled Python timer callback,
not the effect. The helper now lets the click finish before opening popups,
positions tooltips at the real cursor and avoids an intermediate screenshot
before the readiness check. The complete final light/dark Xwayland runs pass;
failed exploratory runs are not counted above. Python callback failures also
leave an explicit `client-error.txt` instead of a silent Qt abort.

### Separate submenu selection checkpoint — 2026-11-05

The supplied macOS screenshot is stored in the Control Center repository as
`desktop-context-menu-sort-by-submenu.png`. It contains both the muted mauve
hover on the parent `Sort By` row and the blue selected `Kind` row in its child
menu. The Light Kvantum profile's shared selected-row color was therefore
changed to a muted plum/mauve (`#8a4b64`, opacity 0.90). The bundled Kvantum
1.1.8 Qt 6 engine now paints a rounded `#556fc4` selection only when the
selected row belongs to a submenu; it identifies the submenu through the
submenu action's association with its parent `QMenu`. Parent rows retain the
existing Kvantum hover path. The engine patch is
`src/offline/kvantum-engine/tahoe-menu-selection.patch`, applied after the
bundled archive digest and path checks during extraction.

Measured from the original 1011 × 730 reference and the isolated real Plasma
render, the root hover sample is `(132, 72, 101)` in macOS and `(133, 69, 98)`
in KDE. The selected child sample is `(85, 111, 196)` in both, because the
patched engine uses that sampled solid blue. The KDE render used the actual
Folder View actions and its `Create New` submenu; this validates the two
selection states on the real Plasma menu path, not Finder's action labels.

The current capture is
`/tmp/tahoe-plasma-menu-glass-u-selection-final-20261105/desktop-context-menu-submenu.png`.
The paired capture with `liquidglass` unloaded is
`/tmp/tahoe-plasma-menu-glass-u-selection-final-20261105/desktop-context-menu-submenu-glass-off.png`.
The isolated test's KWin process loaded the private effect and Plasma mapped
the patched Kvantum library, recorded in `liquidglass-loaded.txt` and
`kvantum-patched-loaded.txt`. Pixel comparison reports 9,752 pixels changed by
more than 8 channel levels in the root-menu crop and 22,826 in the submenu
crop; the sampled 900 × 900 desktop region outside the panels has no changed
pixels. This shows the effect is separately visible on each popup surface
without changing the desktop outside them. It does not by itself prove a
pixel-perfect match of blur or refraction.

The tested config uses 5 px submenu overlap and a 14 px popup radius. The
panels meet, but a doubled seam remains visible at their join; their outer
silhouette is not yet the continuous U-shaped reference. KDE's real action
labels also make its root and submenu wider/taller than Finder's. Those visual
gaps remain open; no screenshot is being called a finished match. The private
session used display `:196`, private D-Bus and private XDG directories and was
stopped after capture; the active desktop was not changed.

### Distro-owned Qt 6 Kvantum deployment path — 2026-11-05

`dpkg -S /usr/lib/x86_64-linux-gnu/qt6/plugins/styles/libkvantum.so` identifies
the current host's Kvantum plugin as the `qt-style-kvantum` package; it has no
project ownership marker. The installer therefore preserves that system file
and builds the same patched engine into a user-owned Qt plugin overlay. A
managed Plasma login script prepends the overlay path through `QT_PLUGIN_PATH`;
the ordinary Kvantum style key and selected theme remain in use. The overlay,
environment-file collision handling, hash-owned uninstall, and distro-plugin
preservation have unit coverage in `tests/test_kvantum_step.py`.

The earlier isolated render used the same Qt mechanism (`QT_PLUGIN_PATH` with
the patched plugin before the distro search path) and confirmed the patched
plugin was loaded in Plasma. The install helper and generated login script have
unit coverage, but a full Plasma login with the overlay installed has not yet
been run on Rebecca. No environment file or plugin was installed on the active
host; the blue-child change will take effect after installation and the next
login.
