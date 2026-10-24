#version 140

#define LG_SAMPLE(tex, coord) texture(tex, coord)
#define LG_OUT fragColor

#include "sdf.glsl"
#include "blur.glsl"
#include "distort.glsl"
#include "highlight.glsl"

uniform sampler2D texUnit;
uniform mat4 colorMatrix;
uniform float offset;
uniform vec2 halfpixel;
uniform vec4 box;
uniform vec4 cornerRadius;
uniform float opacity;
uniform float rgbDriftStrength;
uniform float magnifyGlassStrength;
uniform float refractionWidth;
uniform float highlightWidth;
uniform float highlightStrength;
uniform float materialOpacity;
uniform float centerOpacity;
uniform bool dockSurface;
uniform vec2 backgroundSize;
uniform vec4 gradientTop;
uniform vec4 gradientBottom;
uniform bool darkGradientOverlay;

in vec2 uv;
in vec2 vertex;
out vec4 fragColor;

void main()
{
    vec2 halfSize = blurSize * 0.5;
    vec2 pos = vertex - box.xy;

    float d = lgRoundedRectDistance(pos, halfSize, cornerRadius);
    float mask = lgRoundedRectCoverage(d);
    if (mask <= 0.0) {
        discard;
    }

    vec2 outNorm = lgRoundedRectNormal(pos, halfSize, cornerRadius, cornerSquircle);
    float inside = max(-d, 0.0);
    float materialPresence = sqrt(clamp(opacity, 0.0, 1.0));
    float lensStrength = magnifyGlassStrength * materialPresence;
    float driftStrength = rgbDriftStrength * materialPresence;
    float reflectionStrength = highlightStrength * materialPresence;

    float refrBand = max(refractionWidth * (dockSurface ? 1.25 : 1.0), 1.0);
    float edgeT = smoothstep(-refrBand, 0.0, d);
    // Keep the Dock's refraction near the rim.
    // Both profiles leave the centre undistorted.
    float edgeQ = edgeT * edgeT * (dockSurface ? 1.0 : edgeT);

    vec2 lensUV = uv;
    vec3 lensNormal = vec3(0.0, 0.0, 1.0);
    if (lensStrength > 0.0) {
        lensUV = lgLensUV(uv, pos, lensStrength, refrBand, blurSize, backgroundSize,
                          cornerRadius, cornerSquircle, lensNormal);
        if (dockSurface) {
            vec2 radial = pos / max(halfSize, vec2(1.0));
            radial /= max(length(radial), 0.001);
            vec2 dockNormal = normalize(mix(outNorm, radial, 0.65));
            vec2 textureNormal = vec2(dockNormal.x, -dockNormal.y);
            float thickness = min(min(blurSize.x, blurSize.y) * lensStrength * 3.5,
                                  refrBand * 0.45);
            lensUV = clamp(lensUV - textureNormal * thickness * edgeQ
                           / max(backgroundSize, vec2(1.0)), 0.0, 1.0);
        }
    }
    vec2 texel = halfpixel * 2.0;
    vec3 col;
    if (offset > 0.0) {
        col = lgGaussianBlur(texUnit, texel, lensUV, offset);
    } else if (lensStrength > 0.0) {
        col = LG_SAMPLE(texUnit, clamp(lensUV, 0.0, 1.0)).rgb;
    } else {
        // Pixel-exact passthrough: snap to texel center so GL_LINEAR returns
        // the underlying texel exactly instead of a sub-pixel bilinear blend.
        vec2 snapped = (floor(lensUV / texel) + 0.5) * texel;
        col = LG_SAMPLE(texUnit, clamp(snapped, 0.0, 1.0)).rgb;
    }
    if (driftStrength > 0.0) {
        col = lgApplyRgbDrift(texUnit, col, lensUV, outNorm, blurSize, driftStrength, edgeQ);
    }
    if (reflectionStrength > 0.0) {
        col = lgApplyHighlight(col, inside, outNorm, pos, blurSize,
                               highlightWidth, reflectionStrength, dockSurface);
        if (!dockSurface && lensStrength > 0.0) {
            col = lgApplyLensReflection(col, lensNormal, reflectionStrength);
        }
    }

    vec4 surface = vec4(col, 1.0) * colorMatrix;
    if (darkGradientOverlay) {
        // Frame-local geometry keeps top/bottom upright on all backends.
        // Tint changes color only: the bottom retains the same blurred glass.
        float heightFraction = clamp((pos.y + halfSize.y) / max(blurSize.y, 1.0), 0.0, 1.0);
        float t = smoothstep(0.0, 0.55, heightFraction);
        float tintAlpha = mix(gradientTop.a, gradientBottom.a, t);
        vec3 tint = mix(gradientTop.rgb * gradientTop.a, gradientBottom.rgb * gradientBottom.a, t);
        surface.rgb = surface.rgb * (1.0 - tintAlpha) + tint;
    }
    // Only the Dock reveals sharp backdrop through its centre. Applet popups
    // need full blur coverage behind their thin client fills.
    float coverage = materialOpacity * (dockSurface ? mix(centerOpacity, 1.0, edgeQ) : 1.0);
    LG_OUT = surface * (mask * opacity * coverage);
}
