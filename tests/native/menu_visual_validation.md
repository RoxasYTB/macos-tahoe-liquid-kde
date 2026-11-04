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
