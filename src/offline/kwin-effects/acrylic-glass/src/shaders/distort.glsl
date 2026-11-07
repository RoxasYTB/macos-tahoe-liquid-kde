// MacTahoe Liquid KDE — Acrylic Glass lens + chromatic distortion helpers

#ifndef LIQUIDGLASS_DISTORT_GLSL
#define LIQUIDGLASS_DISTORT_GLSL

float lgLensSoftMax(float a, float b, float width)
{
    float difference = abs(a - b);
    return 0.5 * (a + b + difference * (1.0 - exp(-difference / width)));
}

float lgLensDistanceAndNormal(vec2 position, vec2 halfSize, vec4 cornerRadius,
                              float squircleBlend, out vec2 outwardNormal)
{
    float radius = position.x > 0.0
        ? (position.y > 0.0 ? cornerRadius.y : cornerRadius.w)
        : (position.y > 0.0 ? cornerRadius.x : cornerRadius.z);
    vec2 q = abs(position) - halfSize + radius;
    vec2 outside = max(q, 0.0);
    float outsideLength = lgCornerLength(outside);
    float width = max(min(radius * 2.0, 48.0), 4.0);
    float difference = q.x - q.y;
    float differenceMagnitude = abs(difference);
    float falloff = exp(-differenceMagnitude / width);
    float derivative = 1.0 - (1.0 - differenceMagnitude / width) * falloff;
    float xWeight = 0.5 * (1.0 + sign(difference) * derivative);
    float smoothMaximum = lgLensSoftMax(q.x, q.y, width);
    float inside = min(smoothMaximum, 0.0);
    float distance = outsideLength + inside - radius;
    if (outsideLength > 0.001) {
        outwardNormal = lgRoundedRectNormal(position, halfSize, cornerRadius, squircleBlend);
    } else {
        outwardNormal = normalize(vec2(xWeight * sign(position.x),
                                       (1.0 - xWeight) * sign(position.y)));
    }
    return distance;
}

vec2 lgLensUV(vec2 uv, vec2 surfacePosition,
              float magnifyGlassStrength, float refractionWidth,
              vec2 surfaceSize, vec2 backgroundSize, vec4 cornerRadius, float squircleBlend,
              bool dockSurface, out vec3 surfaceNormal)
{
    float apertureRadius = min(surfaceSize.x, surfaceSize.y) * 0.5;
    vec2 halfSize = max(surfaceSize * 0.5, vec2(1.0));
    vec2 outwardNormal;
    float signedDistance = lgLensDistanceAndNormal(surfacePosition, halfSize, cornerRadius,
                                                   squircleBlend, outwardNormal);
    // The smooth lens distance above is intentionally softened for the old
    // dome model. The Snell profile uses a geometric inset, as the QML SDF
    // does, so its 35 px edge band has the same optical depth at capsule edges.
    signedDistance = lgRoundedRectDistance(surfacePosition, halfSize, cornerRadius);
    float minSurfaceSize = min(surfaceSize.x, surfaceSize.y);
    if (dockSurface) {
        // Keep the established KWin dome model for the Dock. The matching
        // Snell profile below is scoped to Control Center capsule materials.
        float smallSurfaceAttenuation = min(1.0, minSurfaceSize / 128.0);
        float capsuleBoost = 1.0 - smoothstep(64.0, 128.0, minSurfaceSize);
        float lensStrength = clamp(magnifyGlassStrength, 0.0, 0.25)
            * mix(smallSurfaceAttenuation, 1.0, capsuleBoost);
        float bezelWidth = min(max(refractionWidth, 1.0), apertureRadius);
        float depth = min(bezelWidth * lensStrength * 2.0, bezelWidth * 1.25);
        float inset = min(max(-signedDistance, 0.0), bezelWidth);
        float profilePosition = inset / max(bezelWidth, 1.0);
        float profileRemainder = 1.0 - profilePosition;
        float smoothProfile = profilePosition * profilePosition
            * (3.0 - 2.0 * profilePosition);
        float smoothDerivative = 6.0 * profilePosition * profileRemainder;
        float squircleRemainder = 1.0 - smoothProfile;
        float squircleRadicand = max(1.0 - pow(squircleRemainder, 4.0), 0.0);
        float convexSquircle = pow(squircleRadicand, 0.25);
        float convexSquircleDerivative = pow(squircleRemainder, 3.0) * smoothDerivative
            / max(pow(squircleRadicand, 0.75), 0.001);
        float convexBlend = 0.25 * smoothstep(112.0, 128.0, minSurfaceSize);
        float profileHeight = mix(smoothProfile, convexSquircle, convexBlend);
        float profileDerivative = mix(smoothDerivative, convexSquircleDerivative, convexBlend);
        vec2 normalizedPosition = surfacePosition / halfSize;
        float domeBase = max(1.0 - 0.72 * dot(normalizedPosition, normalizedPosition), 0.0);
        float domeProfile = domeBase * domeBase;
        vec2 domeGradient = -2.88 * domeBase * normalizedPosition / halfSize;
        float domeDepth = minSurfaceSize * lensStrength * 1.5;
        float height = depth * profileHeight + domeDepth * domeProfile;
        vec2 heightGradient = -depth * profileDerivative
            * outwardNormal / max(bezelWidth, 1.0) + domeDepth * domeGradient;
        surfaceNormal = normalize(vec3(-heightGradient, 1.0));
        float refractiveIndex = 1.45;
        vec3 incident = vec3(0.0, 0.0, -1.0);
        vec3 refractedRay = refract(incident, surfaceNormal, 1.0 / refractiveIndex);
        float rayDepth = max(abs(refractedRay.z), 0.001);
        float normalView = clamp(surfaceNormal.z, 0.0, 1.0);
        float fresnelBase = (refractiveIndex - 1.0) / (refractiveIndex + 1.0);
        float fresnel0 = fresnelBase * fresnelBase;
        float grazing = pow(1.0 - normalView, 5.0);
        float fresnelTransmission = 1.0 - fresnel0 - (1.0 - fresnel0) * grazing;
        float slabThickness = depth * 0.35 + height;
        float rimFadeWidth = min(bezelWidth * 0.25, 12.0);
        float rimFade = smoothstep(0.0, max(rimFadeWidth, 1.0), inset);
        vec2 offsetPx = refractedRay.xy / rayDepth * slabThickness * fresnelTransmission * rimFade;
        float maxDisplacementPx = min(max(refractionWidth * 0.8, minSurfaceSize * 0.12),
                                      minSurfaceSize * 0.20);
        float displacementPx = length(offsetPx);
        float limitStartPx = maxDisplacementPx * 0.6;
        float limitBlend = smoothstep(limitStartPx, maxDisplacementPx, displacementPx);
        float limitedDisplacementPx = mix(displacementPx, maxDisplacementPx, limitBlend);
        offsetPx *= limitedDisplacementPx / max(displacementPx, 0.001);
        return clamp(uv + offsetPx / max(backgroundSize, vec2(1.0)), 0.0, 1.0);
    }
    // The soft maximum above rounds the normal over a broad 48 px zone. That
    // is useful for the Dock dome, but it invents sideways refraction on the
    // straight edge of short Control Center capsules. Use the actual contour
    // normal and the same Snell-on-a-dome profile as the Control Center's
    // LiquidGlass.qml material.
    outwardNormal = lgRoundedRectNormal(surfacePosition, halfSize, cornerRadius, squircleBlend);
    float edgeBandPx = max(refractionWidth * 0.625, 1.0);
    float insetPx = min(max(-signedDistance, 0.0), edgeBandPx);
    float t = clamp(insetPx / max(edgeBandPx, 1.0), 0.0, 1.0);
    float sinThetaI = (1.0 - t) * (1.0 - t);
    float thetaI = asin(clamp(sinThetaI, 0.0, 1.0));
    float sinThetaT = sinThetaI / 1.7;
    float thetaT = asin(clamp(sinThetaT, 0.0, 1.0));
    float edgeMagnification = tan(thetaI - thetaT);
    float selectedRadius = surfacePosition.x > 0.0
        ? (surfacePosition.y > 0.0 ? cornerRadius.y : cornerRadius.w)
        : (surfacePosition.y > 0.0 ? cornerRadius.x : cornerRadius.z);
    vec2 cornerQ = abs(surfacePosition) - halfSize + selectedRadius;
    float cornerWeight = 1.0 - 0.98 * smoothstep(-12.0, 12.0, min(cornerQ.x, cornerQ.y));
    float aspectRatio = max(surfaceSize.x, surfaceSize.y) / max(minSurfaceSize, 1.0);
    float capsuleFactor = smoothstep(1.7, 2.1, aspectRatio);
    // The calibrated 0.15 KWin value maps to the proven 75 px QML Snell
    // scale. Wider cards keep that profile; compact rounded controls soften
    // it to avoid folds where two edges meet at a corner.
    float refractionScale = clamp(magnifyGlassStrength, 0.0, 0.25) * (75.0 / 0.15)
        * mix(0.30, 1.0, capsuleFactor);
    vec2 offsetPx = -outwardNormal * edgeMagnification * refractionScale * cornerWeight;

    // Bound the grazing-angle peak without flattening the optical profile.
    // The previous 20% cap saturated almost the entire capsule and made
    // strength changes visually indistinguishable; the 45% cap preserves the
    // curved displacement across the visible bezel while protecting corners.
    float safeCapRatio = mix(0.11, 0.45, capsuleFactor);
    float maxDisplacementPx = min(max(refractionWidth * 0.8, minSurfaceSize * 0.12),
                                  minSurfaceSize * safeCapRatio);
    float displacementPx = length(offsetPx);
    float boundedDisplacementPx = displacementPx / sqrt(1.0
        + pow(displacementPx / max(maxDisplacementPx, 1.0), 2.0));
    offsetPx *= boundedDisplacementPx / max(displacementPx, 0.001);

    // KWin's scene UV has its origin at the lower left; surfacePosition and
    // the QML Snell normal use screen coordinates with y increasing down.
    // Flip the vertical pixel offset when converting it to the captured scene.
    vec2 offsetUV = vec2(offsetPx.x, -offsetPx.y) / max(backgroundSize, vec2(1.0));
    surfaceNormal = normalize(vec3(outwardNormal * edgeMagnification, 1.0));
    return clamp(uv + offsetUV, 0.0, 1.0);
}

vec3 lgApplyRgbDrift(sampler2D texUnit,
                     vec3 baseColor,
                     vec2 lensUV,
                     vec2 outwardNormal,
                     vec2 blurSizePx,
                     float rgbDriftStrength,
                     float edgeQ)
{
    vec2 safeSize = max(blurSizePx, vec2(1.0));
    vec2 drift = outwardNormal * (rgbDriftStrength / safeSize);

    float r = LG_SAMPLE(texUnit, clamp(lensUV + drift, 0.0, 1.0)).r;
    float g = LG_SAMPLE(texUnit, clamp(lensUV + drift * 0.30, 0.0, 1.0)).g;
    float b = LG_SAMPLE(texUnit, clamp(lensUV - drift * 0.25, 0.0, 1.0)).b;

    return mix(baseColor, vec3(r, g, b), edgeQ);
}

#endif
