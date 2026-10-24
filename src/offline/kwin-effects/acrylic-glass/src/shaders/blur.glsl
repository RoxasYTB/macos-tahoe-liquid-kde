// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef LIQUIDGLASS_BLUR_GLSL
#define LIQUIDGLASS_BLUR_GLSL

// Dense 5x5 binomial Gaussian, reconstructed with nine bilinear samples.
// Pair weights 4 + 1 at +/-1.2 texels; the centre has weight 6.
// The Kawase pyramid owns the radius except at the two finest strengths,
// which apply this compact kernel directly to the native-resolution capture.
vec3 lgGaussianBlur(sampler2D texUnit, vec2 texel, vec2 uvCenter, float radiusScale)
{
    vec3 total = vec3(0.0);
    float tapSpacing = 1.2 * clamp(radiusScale, 0.0, 1.0);
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float weight = (x == 0 ? 6.0 : 5.0) * (y == 0 ? 6.0 : 5.0);
            vec2 coord = uvCenter + vec2(float(x), float(y)) * texel * tapSpacing;
            total += LG_SAMPLE(texUnit, clamp(coord, 0.0, 1.0)).rgb * weight;
        }
    }
    return total / 256.0;
}

#endif
