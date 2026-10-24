# Glass materials

Open **System Settings → Desktop Effects → Acrylic Glass → Configure**.
Choose a preset, adjust its controls if desired, and press **Apply**.

| Preset | Appearance |
| --- | --- |
| Tahoe | Smooth, rounded convex lensing over translucent glass with a light frosted blur. Default in Tahoe. |
| Golden Gate | Tahoe's optical values with an 85% black tint that fades out at 55% of menu height. The lower 45% and Dock stay untinted. Default in Golden Gate. |

Each preset replaces the complete material: blur, opacity, refraction, color
separation, highlights, grain, brightness, contrast, saturation and gradient.
There is one smooth blur implementation. **Fine tuning** exposes the detailed
controls without requiring a choice of blur algorithm.
Both presets use a blur strength of 0.8 on the 0–20 scale: a restrained,
fine blur that keeps backdrop detail visible through the lens. At the two
finest levels, the first Kawase pass stays at native resolution instead of
shrinking the backdrop. Their
current optical defaults use a 64 px bezel and 0.12 lens strength; these are
project-tuned values, not values supplied by Apple.
Sub-unit blur settings now scale the finest sample spacing continuously down
to zero, so values below 1.0 preserve more backdrop detail for the lens to bend.
Refraction strength is adjustable to 0.12; sampled displacement
remains bounded to prevent folds in the backdrop.
Chromatic dispersion is deliberately restrained to 1 px: stronger per-channel
offsets create colored fringes that read as broken edges rather than clear glass.
The window lens also adds a directional Fresnel/specular reflection derived
from its surface normal. Its tighter specular lobe follows the curved pane;
its tint blends with the refracted backdrop color, so
nearby content colors influence the reflection; intensity follows **Highlight
strength**.

**Glass opacity** controls how much of the blurred material covers the original
background. Keep it at 1 for full material coverage; lower it to reveal more
of the sharp background. The Dock uses a clearer centre while preserving the
refracted rim; applet popups retain full blur coverage. Text and icons retain
their own opacity. Gradient
colors and strengths are independent of this coverage, so a lighter bottom
does not lose its blur. Disable **Enable gradient** for an untinted material.

Selecting another preset replaces your material adjustments. **Restore this
preset** reapplies the selected preset, including its gradient colors.
**Cancel** discards pending changes. Saved adjustments survive reopening the
settings. Installing or reinstalling Acrylic Glass reapplies the complete
preset of the repository being run: **Tahoe** from Tahoe, **Golden Gate** from
Golden Gate. This replaces previous material selections and optical adjustments,
including the gradient toggle and colors. Corners and window rules remain
independent and are preserved.

Tahoe Plasma applet popups, tooltips, Qt menus and the detached search capsule
use a 55% white fill in light mode. Dark-mode Plasma popups and Qt menus no
longer add a client-side black fill, leaving the KWin glass material untinted.
Golden Gate installs a nearly clear 1% white fill in dark mode, letting
the upper gradient supply the dark tint while the lower part stays clear.
Golden Gate light native Qt menus use a 60% white translucent surface so their
dark system text remains readable above that gradient. This exception affects
only the light Golden Gate Kvantum menu assets; other Golden Gate surfaces keep
their existing fills.
Text follows the system window foreground throughout. The Dock
uses identical assets in both modes and retains its thin transparent fill.
Contours use a 0.75 logical-pixel dark outer line and a 0.75 logical-pixel
light inner line, following each surface's native rounded mask. The Dock uses
24% opacity on the outer line and 30% on the inner line for a visible thin edge. The gradient
only tints the blurred backdrop; it does not change text, blur coverage,
contours or the Dock. Both editions share surface geometry with edition-specific
fills; there is no separate reduced-transparency mode.
GTK client-side popups keep their own readable fills; KWin cannot blur those
surfaces in the same way as Plasma popups and Qt menus.

## Visual references

These are independently tuned KDE materials, inspired by Apple's published
screenshots and design guidance; they do not reproduce Apple's renderer.

The X11 lens is a GPU height-field approximation: **Refraction width** sets a
rounded-rectangle bezel, and a softly blended edge distance drives a convex
squircle profile that rises from the silhouette and flattens into the pane.
GLSL `refract` applies Snell's law at that surface normal; the ray travels
through the local base-plus-profile thickness, and Fresnel transmission reduces
displacement toward grazing angles. A low-amplitude ellipsoidal height field
adds broad convex-dome magnification across the pane; its analytic gradient
feeds the same surface normal used by refraction and highlights. Blending
neighboring edge distances avoids a crease where the nearest edge changes; the
profile has zero slope at the dome's optical centre and rim. The sampled
displacement is capped at 20% of the smaller surface dimension; shader probes
check the mapping Jacobian at default and maximum lens strength on the reference
surface and five smaller popup sizes, down to 64×48 px. Refraction strength is
bounded to 0.12 for this profile. Apple describes Liquid Glass as dynamic
lensing that bends and concentrates light, but does not publish
its renderer or numeric shader model. This is therefore a transparent,
testable approximation of general lens optics, not Apple's private shader or a
claim of pixel parity. The current dome depth is tuned to 2.625 times the
minimum surface dimension times lens strength. The shader pixel probe checks a
non-negative normalized mapping Jacobian at both the default and maximum lens
strength on the reference surface and five smaller popup sizes, so the lens
cannot silently fold the sampled backdrop as its aspect ratio or scale changes.

To render a deterministic optical comparison, run
`MTTKDE_GLASS_SHADER_CAPTURE_DIR=/tmp/liquidglass-optics pytest -q tests/test_glass_presets.py -k native_glass_shader_pixels`.
It writes a flat control and 0.08/0.12 refraction PNGs over colored bands and
diagonal lines. This isolated shader probe uses software OpenGL under Xvfb; it
checks the optical mapping, not KWin's live GPU/compositor integration.

To smoke-test the freshly built X11 module in a private KWin/Xvfb session, run
`MTTKDE_X11_PLUGIN=/path/to/liquidglass_x11.so pytest -q tests/test_acrylic_glass_x11_smoke.py`.
The test checks that KWin activates and maps that exact module without replacing
the running desktop plugin; it validates loading, not GPU rendering quality.

- [macOS Tahoe 26 introduction](https://www.apple.com/newsroom/2025/06/macos-tahoe-26-makes-the-mac-more-capable-productive-and-intelligent-than-ever/): translucent Dock and controls that reflect the surrounding desktop.
- [macOS Golden Gate](https://www.apple.com/os/macos/): more uniform refraction and improved contrast.
- [Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/): blur and tint preserve legibility, with clearer and more substantial materials for different surfaces.
- [Liquid Glass — SDF, normals, Snell refraction](https://rukkiecodes.github.io/liquid-glass/): an independent, open physics model and GPU shader implementation.
- [Liquid Glass physics and derivations](https://github.com/sohumsuthar/liquid-glass): an independent ray-traced slab model, including thickness and Fresnel transmission.

The Golden Gate preset adds a black upper gradient to menus in both appearance
modes. It starts at 85% opacity and reaches zero at 55% of the surface height.
The lower 45% retains untinted blurred glass. Launcher text has a soft, low-opacity
halo: white behind dark text and black behind light text. The halo is centered
and diffused rather than drawn as a hard outline. In light mode, category pills
use a translucent white backing to separate dark labels from the upper gradient.
The Dock and panels use a clearer surface without the gradient: a smooth blur, less grain and 98% centre
coverage, with a mild angled refraction and a thin bright edge. Its compact
Dual Kawase pyramid uses up to three levels, followed by a dense Gaussian
finish. The finish samples adjacent texels instead of separating image copies.
The Dock uses more blur and less refraction and color separation
to soften the backdrop without stretching it into a wide band.
The Dock's blur taps and centre coverage soften backdrop detail without
making the glass opaque. The lens bends the backdrop inward at an angle near
the rim, with its strength independent of the Dock's length.
These adjustments follow the selected material and its
controls without changing saved settings; contextual menus keep their full blur.
Applet popups retain the selected blur with full centre coverage. Golden Gate
and Tahoe share every optical value; only the gradient differs. These numerical
settings are project tuning, not values supplied by Apple. The black gradient
darkens lighter backdrops and leaves a fully black backdrop black.
