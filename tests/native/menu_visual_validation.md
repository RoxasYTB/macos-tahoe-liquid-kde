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

### Child selection versus pointer hover — 2026-11-05

The earlier patch painted every active child row blue, conflating Qt's
keyboard/current `State_Selected` with the pointer's `State_MouseOver`. The
bundled patch now renders a neutral gray for a selected child row and the Tahoe
blue (`#556fc4`) only when the pointer is over that row. Parent submenu hover
continues to use the existing mauve style.

The patched Qt 6 engine compiled and loaded in an isolated Plasma session. Its
`finder-menu-layout-on.png` capture shows the selected `Kind` row in gray at
`/tmp/tahoe-plasma-menu-state-batch-dark-20261105/finder-menu-layout-on.png`.
The side-by-side visual batch is `/tmp/tahoe-menu-state-batch-comparison.png`;
the macOS side is the supplied hover reference and the KDE side is the
keyboard-selected state. Automated pointer motion closed the test submenu, so
an actual KDE pointer-hover capture is still needed before treating that branch
as visually verified.

The initial config value of 5 did not produce a 5 px rendered overlap: Kvantum
subtracts profile menu shadow depth before Qt places the child. A new isolated
Light-profile A/B used values 9 and 14. At 9 the two visible edges touch; at 14
the child shifts 5 px left and overlaps the root. The calibrated Dark value is
16 because its menu shadow depth is 6 px instead of Light's 4 px. Captures:
`/tmp/tahoe-plasma-menu-overlap9-20261105/desktop-context-menu-submenu.png`
and `/tmp/tahoe-plasma-menu-overlap14-20261105/desktop-context-menu-submenu.png`;
the join crop sheet is `/tmp/tahoe-menu-join-calibration.png`. The current
14/16 values satisfy the measured horizontal overlap, but the outer silhouette
is not yet a continuous U.
KDE's real action labels also make its panels wider/taller than Finder's. The
private sessions used display `:196`, private D-Bus and XDG directories and
were stopped after capture; the active desktop was not changed.

#### Rejected direct `submenu_overlap=5` experiment — 2026-11-05

To resolve whether the configured value itself should be 5, both Light and Dark
were rendered in fresh isolated Plasma sessions with that value. The Dark run
used `/tmp/tahoe-plasma-finder-overlap5-dark-20261105/`; its captured QMenu
geometries are root `[934,198,216,214]` and child `[1144,341,162,292]`.
Compared with the calibrated Dark value 16, the child moves 11 px to the right
and the rendered borders leave a visible gap. The paired Light comparison is
`/tmp/tahoe-menu-join-overlap-ab.png` (reference, Light 14, Light 5). In both
profiles, `5` is therefore rejected as the engine setting; retain Light 14 and
Dark 16, which compensate for profile shadow depth and produce the closer join.

This only resolves panel placement. The join still has a doubled edge and does
not yet read as one continuous U-shaped perimeter; the remaining fix must
address the shared seam/edge painting, not reduce the overlap value. Full Dark
capture: `/tmp/tahoe-plasma-finder-overlap5-dark-20261105/desktop-context-menu-submenu-glass-on.png`.

#### Rejected Kvantum seam-mask prototype — 2026-11-05

A private Qt 6 Kvantum build detected the actual child `QMenu` and its visible
parent, computed their shared geometry, and clipped an 8 px strip from the
child's left surface/frame while they overlap. The isolated Plasma session
loaded that build (verified in `kvantum-patched-loaded.txt`), but the pixels in
the context-menu join were identical to the unmodified capture. Captures:
`/tmp/tahoe-plasma-finder-dark-profile-20261105/desktop-context-menu-submenu-glass-on.png`
and `/tmp/tahoe-plasma-finder-seamclip2-dark-20261105/desktop-context-menu-submenu-glass-on.png`.

This rules out the tested Kvantum `PE_PanelMenu` frame/interior as the source
of the visible join line. The remaining edge appears to be introduced by the
KWin glass pass or another surface layer; treat that as a hypothesis until a
compositor-side A/B confirms it. Do not keep this prototype patch.

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

### Finder reference geometry probe — 2026-11-05

`tests/menu_visual_probe.py --client finder-context` adds a deterministic
visual twin of the supplied Finder context-menu crop. It reproduces the parent
and child labels, mauve parent hover, blue `Kind` selection and checkmark, but
it does not replace or alter Plasma's actual QAction menu; that remains covered
by the `context` case. At the checked-in Light overlap value 14, the private
render reported root QMenu geometry `[934, 198, 216, 210]` and child geometry
`[1135, 339, 162, 288]`. After shadow insets, their visible placement closely
matches the macOS crop. Existing pixel samples put the parent hover at
`(132, 71, 102)` on macOS and `(133, 69, 98)` in KDE, with the child selection
at `(85, 111, 196)` in both.

The fixture was rendered with the private KWin `liquidglass` effect active.
The paired on/off screenshots changed 1,101 pixels in the root and 5,960 in
the child by more than 8 RGB levels, with no changed pixels outside the popup
surfaces. This confirms both menu surfaces are processed by the live effect;
it does not certify a pixel-perfect match of the material.

An attempted Light `submenu_overlap=19` was clamped to 16 by Kvantum 1.1.8's
`qMin(qMax(value, 0), 16)` parser; its measured child x coordinate was 1133,
the same as the value-16 trial. The production values therefore remain 14/16,
which the earlier A/B calibrated to a 5 px visible join. No engine-limit patch
was kept. The 16 trial shows a slightly tighter join but still leaves the
Liquid Glass edge/shadow transition to refine. Screenshots and process logs
from this capped-value diagnostic are under
`/tmp/tahoe-plasma-native-overlap19-20261105/`; the reference remains in the
separate Control Center repository.

### Popup rim highlight calibration — 2026-11-05

The popup rim was already enabled in the earlier private captures: an empty
`WindowBorderClasses` list with `WindowBorderMatching=false` means “all windows
except listed ones,” so the `plasmashell` popups receive the rim. Switching
the filter to an explicit `plasmashell` match produced pixel-identical popup
captures. The edge-strength A/B then held geometry and material constant.
Raising `HighlightStrength` from 0.14 to 0.28 changed only 528 pixels above 8
RGB levels in the menu crop (maximum channel delta 13); raising it to 0.60
created a brighter magenta halo around both panels. That halo diverges from the
reference's restrained, uneven lavender rim and conflicts with the no-rose
material requirement. No effect defaults or production SVGs were changed.
The next edge pass should shape the menu's SVG rim and its directional
highlight together instead of raising the global reflection strength.
Comparison crops are `/tmp/tahoe-menu-rim-reference-compare.png` and
`/tmp/tahoe-menu-highlight-14-60.png`.

### Menu-specific live-glass opacity — 2026-11-05

- The earlier opacity A/B copied the plugin mapped into the active desktop
  (built 2026-11-03), while this repository's isolated build was newer. The
  current source plugin was rebuilt and copied into private Xorg sessions;
  `/tmp/tahoe-plasma-finder-menuopacity70-20261105/liquidglass-loaded.txt`
  confirms KWin mapped that private copy and `effects-active.txt` lists
  `liquidglass`.
- Added `MenuMaterialOpacity`, separate from the general glass opacity, so
  menu tuning does not change the Dock or ordinary glass surfaces. The KCM
  exposes it as “Menu glass opacity.” The Tahoe profile defaults to `0.70`;
  Golden Gate keeps `1.0`.
- With the source-built effect, `MenuMaterialOpacity=0.35` let too much sharp
  wallpaper through the real Plasma menu. At `0.70`, both the Finder fixture
  and the actual Folder View `Create New` submenu retain blur while revealing
  more live desktop. The menu remains on the live compositor path; no wallpaper
  texture is baked into the surface. Captures are under
  `/tmp/tahoe-plasma-finder-menuopacity35-20261105/` and
  `/tmp/tahoe-plasma-finder-menudefault-20261105/`.
- The latter private capture omitted `MenuMaterialOpacity` from `kwinrc`, used
  `BlurStrength=1.0`, and confirmed the new KConfig default is used. The KWin
  effect and its configuration module both build successfully from
  `work/liquidglass-build`; JSON/XML parsing and `git diff --check` pass.
- The same source-built plugin was rendered with the dark Plasma color scheme
  and dark Kvantum profile in `/tmp/tahoe-plasma-finder-dark-profile-20261105/`.
  `effects-active.txt`, `liquidglass-loaded.txt` and
  `kvantum-patched-loaded.txt` identify the live private components; the
  captured desktop menu and submenu keep the same light wallpaper behind them.
- This is an opacity calibration, not completion of the menu reproduction.
  The connected U-shaped join still has a doubled edge in the deterministic
  fixture; the directional, restrained Liquid Glass contour and the dark
  profile still need fresh side-by-side renders.


#### Compositor-side shared submenu strip prototype — 2026-11-05

A narrow prototype now uses the native transient-parent relationship and measured window intersection. Kvantum leaves the intersecting panel strip transparent; the KWin shader discards its child-glass pixels over that same strip so the parent glass can show through. This preserves separate QAction menus and the calibrated Light 14 / Dark 16 overlap values.

Both patched components compile: Kvantum 1.1.8 and the KWin X11 and Wayland effect builds. The host is missing the XCB shared-memory development header, so I supplied a build-only header shim under `/tmp`; no system package or active-session config was changed. An isolated KWin Wayland + XWayland fixture loaded Liquid Glass and the patched Kvantum engine. Its on/off capture differed by 37,694 pixels above 8 RGB levels within the popup regions, confirming that the live effect processed both menus. Screenshot: `/tmp/tahoe-menu-join-wayland-20261105e/finder-context/on.png`; geometry: root `[884,198,216,210]`, child `[726,339,162,288]`. The fixture placed the child to the left because its virtual screen is only 1100 px wide; the current screenshot confirms a 4 px rendered overlap, but does not yet establish a clean shared U-shaped contour against the supplied wallpaper/reference. Do not call the prototype finished or copy it into the active desktop until a right-opening reference-sized render confirms the seam.

#### Parent hover redraw and inset capsule — 2026-11-05

The reference-sized 1920 × 1080 XCB/KWin fixture now keeps the root `Sort By` row highlighted while the pointer is over child `Kind`. Kvantum identifies a submenu from `QMenu::parentWidget()` and requests a redraw of the matching parent action when the child is hovered; `QAction::associatedObjects()` was not a reliable root/submenu classifier. The parent highlight is now a 5 px horizontal / 2 px vertical inset rounded capsule using the theme's existing mauve treatment. At aligned samples, reference `(420,320)` is RGB `(132,73,100)` and KDE `(1020,365)` is `(132,72,100)`; another KDE interior sample is `(134,73,100)`. Child hover blue remains visible.

Capture: `/tmp/tahoe-menu-join-parent-pill-20261105/finder-context/on.png`; side-by-side crop: `/tmp/tahoe-menu-parent-pill-comparison.png`. The joined panels still show two outlines at their overlap. That remaining U-rim defect is separate from row hover styling and needs the next isolated render pass.

#### Parent-child join detection and overlap batch — 2026-11-05

- Replaced the Kvantum join clip's `associatedObjects()+activeAction()` lookup with the stable `QMenu::parentWidget()` relation. The previous lookup could fail while the pointer was already inside the child menu. The patched Qt 6 engine builds and was loaded in a fresh isolated KWin/XCB screenshot session.
- At the production Light value 14, geometry is root `[934,198,216,210]`, child `[1135,339,162,288]`. The paired render is `/tmp/tahoe-parent-widget-qmenu-20261105c/finder-context/on.png`; the macOS / Light 14 / temporary 22 comparison is `/tmp/tahoe-menu-overlap-matrix-20261105.png`.
- KWin on/off changed 330 parent-menu pixels and 42,606 child-menu pixels above 8 RGB levels; the sampled desktop outside both popups had no changed pixels. This confirms both rendered popup surfaces still receive live glass in this capture.
- A private-only overlap-22 trial raised Kvantum's parser limit to 32 and moved the child frame to x=1127. It did not remove the separate inner edge and obscured more of the parent row; reject 22 and keep production overlap at Light 14 / Dark 16.
- The parent-child lookup fix is useful plumbing, but the screenshots still show a small visible separation/doubled edge. Do not call the U-shaped join complete. The next batch should change the join edge treatment itself, not increase overlap again.


### 2026-11-05: native submenu ownership and application edge

The Kvantum patch now resolves detached native submenus through the owning
QAction's associated menus, validating action ownership and visibility. The real
Plasma Create New submenu now paints pointer selection blue while its open parent
row remains mauve. The menu edge uses the Aurorae application's one-pixel white
line at 12% opacity, painted after the interior instead of stretching an SVG stroke.

Private Xorg/DBus capture: `/tmp/tahoe-menu-owned-submenu-glass-only-20261105/`.
`effects-active.txt` contains only `liquidglass`; process maps prove the rebuilt
Kvantum and copied glass plugin were loaded. Parent geometry is 320x210 at
(1000,327), child 201x314 at (1307,331): 13 pixels of window overlap minus
two four-pixel transparent margins gives five pixels of visible overlap.
The light/dark profiles use overlap 12/16 to account for their 4/6-pixel margins.
The dark profile's new geometry has configuration coverage, not a new live capture.

Build: bundled Kvantum 1.1.8 with the regenerated patch, target `kvantum`, succeeds.
Targeted tests: 11 passed, 3 skipped (`test_menu_rounding.py`,
`test_popup_rendering.py`); `git diff --check` passes.

This is a checkpoint, not a pixel-identical result. The application edge's white
line is reused, but the reference's outer dark outline and its full rim response
still differ. Reference and KDE menus lie over different wallpaper regions, so
these captures do not establish matching blur/refraction strength. KDE action
contents, icon colors and resulting panel dimensions differ intentionally.
No active desktop configuration was changed.


### 2026-11-05: explicit menu surface and neutral live material

Kvantum now publishes its actual painted QMenu rectangle to BlurHelper. Its
rounded blur region excludes the native transparent shadow margins. Registration
also covers menus that were translucent before polish. Geometry changes trigger
one delayed blur-region update; unchanged paints do not rewrite the property.
The existing `popup_blurring` preference gates this path. The private X11 capture
records both `_KDE_NET_WM_BLUR_BEHIND_REGION` properties with a four-pixel inset
and nine-pixel corner geometry. This removes the exposed wide compositor rim.

The native edge now uses the application's adjacent one-pixel black/white lines,
both at 12% opacity. The scalable SVG stroke is removed. Both native menu center
assets use neutral black at 50% opacity. The dark installer recognizes the current
material opacities, clears the obsolete frame, and preserves the chosen center
opacity; the corresponding test checks asset/staged consistency and idempotence.
No saturation/contrast experiment is retained in the KWin effect.

Native QMenu layout now has five pixels of vertical interior padding. The paint
rectangle excludes shadow only, so padding cannot shrink the glass surface. Text
height remains derived from the application's font; native padding is nine pixels
instead of QCommonStyle's eight. Combo/QML paths retain their previous geometry.
The menu-item layout frame remains three pixels, expansion remains 12, and
separators, action model and horizontal text margins are unchanged. The explicit
visual-fidelity request takes priority over the earlier unchanged-row-height rule.
Pointer selections occupy the full native row; child rounding is six pixels.

Verification directory: `/tmp/tahoe-menu-native-spacing-final-20261105/`.
Only `liquidglass` was active; maps verify both rebuilt plugins. The system's
actual SF Pro Text 10-point settings and user font directory were provided to
this private session. The test wallpaper was aligned to the supplied reference
at width 2560, crop origin (1117,224). An RGB calibration fitted only outside menu
regions reduces substrate mean errors to (0.82,0.69,0.89) levels per channel.
That calibrated substrate is private test data, not an application background.

The live foreground probe is a separate, unglassed, non-focusing Qt window. Its
change affects 24,509 sampled parent pixels and 25,208 child pixels above eight
RGB levels. Both sampled gray surfaces have zero median chroma: no fixed purple
client tint remains. On/off captures also establish compositor work on both
surfaces (365 and 3,633 sampled pixels above eight RGB levels respectively).
The blue row is 24 pixels tall, matching the reference; its current y range is
400..424 versus 402..426 in the reference fixture. The comparison remains a
fixture, not a replacement for Plasma actions or a claim of pixel identity.

Built bundled Kvantum and the X11 glass effect successfully. Archive-plus-patch
reapplication exactly reproduces both compiled Kvantum source files. Targeted
menu, popup, surface and glass-config checks: 31 passed, 28 skipped. The skipped
render checks require unavailable optional QtSvg bindings. Actual X11 screenshots
are reviewed separately. No active session settings were modified.


### 2026-11-05: calibrated native material, checked actions and full row geometry

The Tahoe native-menu shader resolves material coverage against the existing
live sharp texture before an achromatic vibrancy curve. Advanced KConfig defaults:
`NativeMenuChromaGain=1.2601`, `NativeMenuLumaGain=-0.4897`,
`NativeMenuLift=0.05582`. Luminance uses (0.2126,0.7152,0.0722), and all three
channels receive the same scalar operations: neutral backing remains neutral.
The operation reuses sharpTex in the compositor shader. No colored overlay or
wallpaper image is used. Only menu roles with MaterialPreset 1 enter this path;
other windows, applets and the Control Center's Qt.Tool retain their prior path.

Calibration used nine bounded variants, then 27 and an empirical renderer-response
fit. Repeating an identical configuration before/after candidates produced zero
maximum pixel difference in the menu crop. The final default render has RGB MAE
2.93167 over 20,948 masked material pixels, versus 11.96023 before calibration
(75.5% reduction). Channel MAEs: (3.59643,1.16059,4.03800). Text, selections,
separators and borders are excluded: this is not whole-interface pixel identity.

`tests/native/menu_material_calibration.py` is a manual NumPy/Pillow scoring and
response-fitting tool. It reads external reference/baseline paths and a directory
of captures with a headerless TSV manifest (name/chroma/luma/lift). The reference
image stays outside this repository. Arguments: `--reference <reference.png>
--baseline <baseline.png> --captures <variants> --output <report.json>`.

Native layout, paint and polish share QAction ownership lookup, including detached
submenus before show. Root icon/text columns gain nine leading pixels. Checked
native actions paint a plain tick and reserve a shared 16-pixel check column;
exclusive/non-exclusive action behavior is unchanged. Native separators are
one-pixel white lines at 40/255 alpha, inset 18/16 in roots and 16/16 in children,
mirrored for RTL. Combo/QML paths keep their prior drawing.

Qt clips each action's paint to its rectangle, so translating selection paint
cropped the bottom. The fix uses actual contents margins: +2 top for both roles,
+1 bottom for roots. Glyph paint compensates vertically. Original application
margins are saved and restored on unpolish. A compiled-engine regression exercises
custom root/child margins through Fusion -> Kvantum -> Fusion twice, verifying
exact restoration and no accumulation. See the [Qt QMenu layout and paint loops](https://github.com/qt/qtbase/blob/6.8/src/widgets/widgets/qmenu.cpp).
The rendering probe now forwards QT_PLUGIN_PATH; the restoration test requires
MTTKDE_TEST_KVANTUM_PLUGIN_PATH to avoid silently testing a stock system engine.

Final private X11 evidence: `/tmp/tahoe-menu-native-final-proof-20261105/`.
Visible fixture surfaces are 207x201 at (330,161) and 151x272 at (532,303), matching
the reference; overlap is five pixels. Both reference and KDE blue fields occupy
y=402..426. Rounding is six pixels. The fixture uses a real checked QAction.

The same session opens the real Plasma Create New menu and its native submenu
(`real-plasma-menu.png`). A separate non-focusing foreground window changes from
blue to gray underneath: 27,833 parent and 27,671 child sampled pixels change above
eight RGB levels. Both gray surfaces have zero median chroma and 95th-percentile
chroma at most one level. Geometry, loaded plugin maps, private display/config
and sole active liquidglass effect are recorded alongside. There are no explicit
NativeMenu overrides in that configuration: these are compiled defaults.

Bundled Kvantum and the X11 effect build successfully. Archive-plus-patch
reapplication reproduces all three compiled Kvantum files exactly. Final compiled
engine/menu/surface/config checks: 32 passed, 28 skipped. Material/config/layout
preset checks: 39 passed, one skipped. Binding/SDK skips are not rendered evidence;
the actual X11 captures are reviewed separately. No active desktop was restarted
or reconfigured, and no pull request was opened.

The final regression also checks that an unselected row under the cursor is not
painted after keyboard selection moves elsewhere, and that disabled rows never
receive a selection fill. The preceding binary fails this negative control at
the old-pointer-row assertion; the final compiled binary passes. Unpolish clears
the cached menu surface as well as restoring application-owned contents margins.

### 2026-11-05: lateral contour registration

The black outer stroke previously extended into the lateral shadow margin.
Inset the pair horizontally by one logical pixel, preserving its existing
vertical placement, radii and Aurorae-derived black/white alpha (31/255).
A symmetric inset was rejected because it worsened the upper edge. The
archive-plus-patch source exactly matches the rebuilt Kvantum source.

Private X11 evidence: `/tmp/tahoe-menu-native-edge-x-20261105/`. Relative to
`native-final-proof`, RGB MAE in narrow, text-free contour strips falls from
32.7072 to 25.2056 on the parent left and 33.5820 to 24.8986 on the child right.
The upper strips remain identical (34.7275 parent, 33.2056 child). These are
local edge measurements, not whole-menu fidelity scores. Both real Plasma
menus and changing live foreground captures were retained in the same session.
Compiled-engine targeted checks: 32 passed, 28 skipped.

Remaining visible differences include weaker contour contrast, the optical
rim/backing detail, and text raster/baseline differences. The reference-labelled
Qt fixture uses locally hand-drawn test pictograms, not the actual KDE icon
pack: their mismatch must not be attributed to the installed icon theme. The
real Plasma captures remain authoritative for native actions and their icons.
No active desktop settings were changed.

### 2026-11-06: preserve live backing beneath the inner rim

The native translucent menu painted its 12% white rim over the 50% black
client veil. This suppressed both contrast and the compositor's chromatic
backing. Paint that one-pixel stroke with CompositionMode_Source instead:
its RGB/alpha replace the veil locally. The white alpha stays 31/255, matching
the application edge; there is no fixed colored border. Opaque/non-composited
menus retain SourceOver. The adjacent dark keyline is 217/255 for translucent
menus and retains 31/255 for opaque menus. Save/restore contains the painter
composition change. Actions, interior material and menu geometry are unchanged.

The isolated comparison shows narrow-strip RGB MAE changes (previous -> new):
parent left 25.2056 -> 7.7794; parent upper 34.7275 -> 4.8517; child right
24.8986 -> 10.8559; child upper 33.2056 -> 6.9983. These exclude most menu
pixels and do not establish full-interface pixel identity. At a representative
parent edge pixel (331,210), reference RGB is (211,77,170), previous KDE
(119,53,95), and corrected KDE (207,75,159).

Evidence before the opaque-path guard: `/tmp/tahoe-menu-native-clear-rim-20261105/`.
A real Plasma Create New menu and native child remain live over a separately
changing blue/gray foreground: sampled parent/child regions change at 42,728 /
24,461 pixels above eight levels, with median gray chroma zero. Final exact-source
capture is `/tmp/tahoe-menu-native-clear-rim-verified-20261106/`.

A separate 27-render optics batch tested widths 16/32/56, lens strengths
0/0.125/0.25, and highlight strengths 0.14/0.5/1. Its masked material-edge
score improves only slightly with width 16 (3.4061 versus 3.4654 at width 56);
stronger highlights do not solve the suppressed client rim. Those experimental
settings were not applied to the active desktop or committed as new defaults.

The final guarded source builds successfully and produces a zero maximum pixel
change in the aligned menu crop compared with the accepted translucent-path
capture. Archive-plus-patch reapplication matches the compiled source. Targeted
compiled-engine checks: 32 passed, 28 skipped. No PR or active-session change.

### 2026-11-06: native flat pane and separator rhythm

Tahoe native-menu refraction is capped at 16 logical pixels (a smaller configured
width remains respected). The legacy/core shaders fade lens UV displacement and
lens normal with the same perimeter weight. This removes the global dome from
native menus while retaining the live bevel, blur and rim. Other materials,
application windows, Dock and Control Center keep their previous optics.

Native separators gain one logical pixel of height. Remove the compensating
extra two top contents pixels and the opposite glyph translation; the two
separators now account for the actual vertical rhythm. Preserve the application
margin save/restore and root bottom inset. Separator strokes are registered at
rect.center.y + 0.5. Native glyph painting shifts one logical pixel toward the
leading edge, mirrored for RTL. Font settings and QML/combo rendering are intact.

Exact-source private evidence: `/tmp/tahoe-menu-native-final-rhythm-20261106/`.
The nine measured child labels from Snap to Grid through Tags have identical
leading x/y bounds to the reference, e.g. (557,350), (557,386), (557,409),
(557,433), through (557,554). Some trailing bounds still differ by one pixel.
`text-alignment.json` records both sets. Parent/child fixture windows remain
215x209 and 159x280: the spacing correction does not enlarge these panels.
The child is manually moved after the recorded geometry as in prior captures.

The session also captures genuine Plasma menus over changing blue/gray backing:
42,545 parent and 24,925 child sampled pixels change above eight RGB levels;
median gray chroma is one level in each. Only liquidglass is active. The native
engine and X11 effect build, and reapplying the archive patch reproduces the
compiled Kvantum/polish sources. Final targeted checks: 32 passed, 28 skipped.
No active desktop configuration or process was changed. Pixel-perfect glyph
rasterization and the full optical field remain unproven by these checks.

### 2026-11-06: soften native menu backing without darkening the material

Eight isolated blur variants (0, 0.5, 1, 2, 3, 4, 6, 8) showed that the flat
native pane needed a compact pyramid instead of the application's near-sharp
source-resolution blur. The level-8 variant reduced sampled material-edge MAE
from 4.3899 to 3.3668 and interior MAE from 4.1280 to 3.1680. This is a masked
optical comparison, not a whole-interface score.

When Tahoe native menus have enabled blur below level 8, draw with the same
pyramid count/offset as level 8. Keep the existing source-resolution behavior
for applications and other popups. Explicit zero blur and settings >=8 use the
normal configured path. No client opacity, material color or refraction changes.
Prepaint expansion uses the corresponding pyramid's extent, so backing pixels
around changing menus are refreshed consistently with the sampling radius.

Exact-source evidence: `/tmp/tahoe-menu-native-material-blur-verified-20261106/`.
Repeated native-menu captures at configured levels 1, 4 and 8 are pixel-identical
in the aligned menu crop; zero blur differs by up to 77 levels. The first draft
used the lower table entry's iteration count and failed this equality check;
the final decode matches the normal fractional-strength path's upper iteration
entry and lower offset. `blur-checks.json` records the passing comparison.

Both genuine Plasma menus remain live over blue/gray foreground changes:
44,212 parent / 24,917 child sampled pixels change above eight levels, with
median gray chroma one level. Sole active effect is liquidglass. X11 effect
build succeeds; final targeted checks: 32 passed, 28 skipped. All work remained
in the private display/config. No active desktop settings or processes changed.

### 2026-11-06: refine neutral material response after blur calibration

Five finite-response captures (baseline, separate chroma/luma/lift perturbations,
repeat baseline) fit the real renderer rather than guessing its alpha/gamma.
Baseline repeats are pixel-identical. The fitted candidate was then captured
before/after the old curve and repeated in a fresh private session.

New native-menu defaults: chroma 1.2563, luma -0.48823, lift 0.04475.
Over 22,327 masked material pixels, measured RGB MAE falls from 3.19441 to
1.70738; channel errors are (1.59865, 0.78080, 2.74269). This excludes glyphs,
selections, separators and outlines, and is not a full-interface fidelity score.
No fixed tint or opacity change is introduced; equal-channel inputs retain
neutrality through the scalar/luminance curve. Other window roles are unchanged.

Exact-source evidence: `/tmp/tahoe-menu-native-tone-verified-20261106/`.
The initial capture with compiled defaults exactly matches the explicitly
configured candidate. Repeated old/new curves each have zero maximum pixel
difference. The real Plasma parent/child remain live over foreground changes:
43,754 / 24,901 sampled pixels change above eight levels, with median gray chroma
one level. X11 effect builds successfully. Final targeted checks: 32 passed,
28 skipped. The active desktop was not modified, and no PR was opened.

### 2026-11-06: register the parent right/bottom contours

Reference edge scans locate the parent's bright right line at x536 and dark
line at x537; the previous Qt fixture put them at x535/x536. The lower bright
line belongs at y360, not y361. The child edges already match and stay intact.
Root native item sizing gains one trailing pixel (mirrored RTL), and the root's
extra bottom contents margin is removed. The reference fixture is 216x208,
replacing its previously incorrect fixed 215x209. It uses the same native style
and real QActions; production menus still derive width from their contents.

With no remaining margin changes, remove the redundant saved-margin properties
and restore block. Unpolish still clears the cached painted surface. The margin
regression now asserts exact preservation while checking that the actual Kvantum
style is loaded. The previous binary fails that assertion; the new binary passes
through repeated Fusion/Kvantum cycles and selection-state checks.

Exact-source evidence: `/tmp/tahoe-menu-native-parent-bounds-20261106/`. Right
strip RGB MAE drops 60.9449 -> 9.8495; lower strip 55.8306 -> 12.2236. These are
local edge strips, not whole-menu scores. Native child remains 159x280, and the
root's text baselines are unchanged. The session also captures genuine Plasma
menus and changing live backing. Both Kvantum source files are reproduced exactly
by archive-plus-patch reapplication. Build succeeds; targeted tests: 32 passed,
28 skipped. The negative-control failure is intentional, not an unresolved test.

### 2026-11-06: compositor-owned native menu shadow

The reference's exterior shadow spans roughly 12-16 pixels; the previous private
Qt render had no measurable exterior shadow. A four-pixel client margin cannot
contain that falloff. BlurHelper now attaches KWindowShadow tiles to the native
QWindow, aligned to the declared painted surface. The Gaussian falloff has
sigma 6, peak alpha 0.29 and a three-pixel downward offset. Its interior is
transparent so the glass's central backing is not darkened. No menu geometry,
QAction or extra overlay window is introduced.

The owned shadow is deleted on blur unregister/style unpolish and with its
QWindow parent. Geometry, native ID and scale are checked before reusing tiles;
resize, WinIdChange and DevicePixelRatioChange trigger buffered updates. XCB
tile pixels/padding scale with window DPR, matching the native backend's raw
pixel protocol. The non-XCB KF path uses logical tiles. NO_KF builds keep the
legacy fallback, with no added dependency. See the [KDE KWindowShadow API](https://api.kde.org/kwindowshadow.html)
and [XCB backend](https://github.com/KDE/kwindowsystem/blob/master/src/platforms/xcb/kwindowshadow.cpp).

Exact-source private X11 evidence: `/tmp/tahoe-menu-native-shadow-verified-20261106/`.
Both parent and child publish eight valid shadow pixmaps plus paddings
(17,16,17,16). Four exterior-strip RGB MAEs fall as follows: left
6.5439 -> 1.1741, top 3.0083 -> 0.6505, right 6.2888 -> 1.0440,
bottom 11.3298 -> 1.6924. These are shadow strips, not whole-interface scores.

`tests/native/menu_shadow_lifecycle.py` is an opt-in private-X11 probe. It verifies
native resource creation, removal under Fusion, recreation under Kvantum and
updated surface geometry after resize. It passes at QT_SCALE_FACTOR 1, 1.5 and 2;
paddings scale to (26,24,26,24) and (34,32,34,32). The probe refuses to start
without MTTKDE_PRIVATE_SHADOW_PROBE=1. The same private session captures actual
Plasma menus and changing foreground backing. Archive-plus-patch reproduces
compiled BlurHelper exactly. Kvantum builds; targeted checks: 32 passed,
28 skipped. Wayland shadow rendering is not qualified by these X11 checks.
No active desktop setting or process was changed.

### 2026-11-06: pointer-driven parent and child selection states

Use actual pointer containment for native rows rather than Qt's potentially
stale State_MouseOver. An open submenu's parent is blue while the pointer is on
that row, and returns to its mauve retained-selection fill when the pointer
enters the child. Apply native leaf selection consistently in roots and children;
open-parent detection also handles nested menus. Disabled/unselected rows do
not gain a fill. Combo/QML paths retain the stock renderer.

The retained parent fill is calibrated to (148,110,131,140), preserving its alpha.
In the text-free reference strip x425..505/y311..329, MAE falls from 3.6745 to
0.3477. Both pointer-blue fills remain opaque (85,111,196). Root/child selected
rows share the fixed native six-pixel contour; inactive parent rounding stays
seven pixels, independent of theme frame.expansion. The former expansion test
now verifies that intended fixed contour plus unchanged geometry at all scales.

Exact-source X11 evidence: `/tmp/tahoe-menu-native-hover-verified-20261106/`.
`parent-pointer.png` samples blue at (480,320); `child-return.png` samples blue
at (650,414), with the parent mauve again. The returned aligned crop is
pixel-identical to the initial child-hover capture. Genuine Plasma menus and
changing live backing are captured in the same session.

The compiled-engine regression checks root parent blue, inactive parent mauve
even with stale State_MouseOver, root leaf blue, and disabled/unselected rows.
Offscreen menus are deliberately non-overlapping. Translucent RGB checks allow
one level of premultiplied quantization while alpha is exact. The prior binary
fails the new root-pointer-blue check; the final binary passes. Build succeeds,
archive patch reproduces the source, and targeted checks finish 32 passed,
28 skipped. No active desktop configuration or processes were changed.

### 2026-11-06: white menu pictograms and inset chevron

Native QMenu icons use white SourceIn tinting with their original alpha mask;
disabled icons use 110/255 white alpha. Prefer the theme's symbolic variant.
Wallpaper and symbolic-link actions fall back to view-preview/insert-link so
opaque colored icon backgrounds do not become solid white blocks. Original
QIcons/assets and non-menu icons are unchanged. Native chevrons and ticks use
white too; chevrons move two logical pixels inward, mirrored in RTL, without
changing action geometry or hit areas.

Exact-source evidence: `/tmp/tahoe-menu-native-symbolic-icons-20261106/`.
The actual Plasma context menu and child show white symbols, including the image
and link fallbacks. The first tint-only draft was rejected after its capture
showed opaque rectangles for those two symbols. The final version also captures
parent/child hover transitions and changing live backing. Kvantum builds and
archive-plus-patch matches the compiled source. Targeted checks: 32 passed,
28 skipped. No active desktop processes or settings were changed.

### 2026-11-06: normal-label vibrancy without changing font size

A private 9.5/9.75/10-point batch was pixel-identical. QFontInfo/QFontMetricsF
confirm all three resolve to the same 13-pixel SF Pro Text and 110.3125-pixel
advance for Date Last Opened. No production font-size change follows that test.
Reference normal-label peaks instead show translucent white: Name reaches
(230,219,229), while the selected blue Kind row reaches opaque (255,255,255).

Enabled native normal/inactive-parent text now uses white alpha 217/255;
pointer-blue selection text retains 255/255. This changes label colors only,
leaving icon tint, checks, geometry, user fonts and disabled labels intact.
The existing renderer applies label alpha independently of icon painting.

Exact-source evidence: `/tmp/tahoe-menu-native-text-opacity-20261106/`.
Name's brightest pixel now exactly matches (230,219,229), and Kind retains
(255,255,255). Across eight text strips, a fixed union-of-bright-pixels metric
falls from 43.6252 to 34.5681. It includes raster/coverage differences and is
not comparable to the material-only MAE. The session also captures genuine
Plasma menus, pointer transitions and changing backing. Kvantum builds;
archive-plus-patch reproduces the compiled source. Targeted checks finish
32 passed, 28 skipped. No active desktop settings or fonts were changed.
