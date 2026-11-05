#extension GL_OES_standard_derivatives : enable

#define LG_SAMPLE(tex, coord) texture2D(tex, coord)
#define LG_OUT gl_FragColor

#include "sdf.glsl"
#include "blur.glsl"
#include "distort.glsl"
#include "highlight.glsl"

uniform sampler2D texUnit;
uniform sampler2D sharpTex;
uniform sampler2D blurFalloffTex;
uniform mat4 colorMatrix;
uniform float offset;
uniform vec2 halfpixel;
uniform vec4 box;
uniform vec4 cornerRadius;
uniform vec4 connectedMenuJoin;
uniform float opacity;
uniform float rgbDriftStrength;
uniform float magnifyGlassStrength;
uniform float refractionWidth;
uniform float highlightWidth;
uniform float highlightStrength;
uniform float materialOpacity;
uniform bool nativeMenuMaterial;
uniform vec3 nativeMenuCurve;
uniform float centerOpacity;
uniform bool dockSurface;
uniform vec2 backgroundSize;
uniform vec4 gradientTop;
uniform vec4 gradientBottom;
uniform bool darkGradientOverlay;

varying vec2 uv;
varying vec2 vertex;

void main(void)
{
    vec2 halfSize = blurSize * 0.5;
    vec2 pos = vertex - box.xy;

    float d = lgRoundedRectDistance(pos, halfSize, cornerRadius);
    float mask = lgRoundedRectCoverage(d);
    if (mask <= 0.0) {
        discard;
    }
    bool inConnectedMenuJoin = lgInsideConnectedMenuJoin(pos, halfSize, connectedMenuJoin);

    vec2 outNorm = lgRoundedRectNormal(pos, halfSize, cornerRadius, cornerSquircle);
    float inside = max(-d, 0.0);
    float materialPresence = sqrt(clamp(opacity, 0.0, 1.0));
    // The parent/child overlap is an interior part of one shared glass shape:
    // retain its material fill, but don't draw a second inner lens or rim there.
    float lensStrength = inConnectedMenuJoin ? 0.0 : magnifyGlassStrength * materialPresence;
    float driftStrength = inConnectedMenuJoin ? 0.0 : rgbDriftStrength * materialPresence;
    float reflectionStrength = inConnectedMenuJoin ? 0.0 : highlightStrength * materialPresence;

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
    vec2 falloffUV = vec2(uv.x, 1.0 - uv.y);
    float blurWeight = LG_SAMPLE(blurFalloffTex, falloffUV).r;
    vec3 sharp = LG_SAMPLE(sharpTex, clamp(lensUV, 0.0, 1.0)).rgb;
    vec3 blurred;
    if (offset > 0.0) {
        blurred = lgGaussianBlur(texUnit, texel, lensUV, offset);
    } else if (lensStrength > 0.0) {
        blurred = LG_SAMPLE(texUnit, clamp(lensUV, 0.0, 1.0)).rgb;
    } else {
        // Pixel-exact passthrough: snap to texel center so GL_LINEAR returns
        // the underlying texel exactly instead of a sub-pixel bilinear blend.
        vec2 snapped = (floor(lensUV / texel) + 0.5) * texel;
        blurred = LG_SAMPLE(texUnit, clamp(snapped, 0.0, 1.0)).rgb;
    }
    vec3 col = mix(sharp, blurred, blurWeight);
    if (driftStrength > 0.0) {
        col = lgApplyRgbDrift(texUnit, col, lensUV, outNorm, blurSize, driftStrength, edgeQ);
    }
    if (reflectionStrength > 0.0) {
        col = lgApplyHighlight(col, inside, outNorm, pos, blurSize,
                               highlightWidth, reflectionStrength, dockSurface);
        if (!dockSurface && lensStrength > 0.0) {
            col = lgApplyLensReflection(col, lensNormal, reflectionStrength, pos, blurSize);
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
    float coverage = inConnectedMenuJoin
        ? 1.0
        : materialOpacity * (dockSurface ? mix(centerOpacity, 1.0, edgeQ) : 1.0);
    if (nativeMenuMaterial && coverage > 0.0) {
        // Resolve coverage against the live, unwarped background before the
        // neutral vibrancy curve. Qt paints its black veil over this result.
        // Equal RGB inputs remain equal: no fixed purple material color.
        vec3 backing = LG_SAMPLE(sharpTex, clamp(uv, 0.0, 1.0)).rgb;
        vec3 material = mix(backing, surface.rgb, coverage);
        float luminance = dot(material, vec3(0.2126, 0.7152, 0.0722));
        surface.rgb = clamp(nativeMenuCurve.x * material + nativeMenuCurve.y * luminance
                            + vec3(nativeMenuCurve.z), 0.0, 1.0);
        coverage = 1.0;
    }
    LG_OUT = surface * (mask * opacity * coverage);
}
