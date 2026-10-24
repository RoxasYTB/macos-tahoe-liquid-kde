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
              out vec3 surfaceNormal)
{
    float apertureRadius = min(surfaceSize.x, surfaceSize.y) * 0.5;
    vec2 halfSize = max(surfaceSize * 0.5, vec2(1.0));
    vec2 outwardNormal;
    float signedDistance = lgLensDistanceAndNormal(surfacePosition, halfSize, cornerRadius,
                                                   squircleBlend, outwardNormal);
    float lensStrength = clamp(magnifyGlassStrength, 0.0, 0.30);
    float bezelWidth = min(max(refractionWidth, 1.0), apertureRadius);
    float depth = min(bezelWidth * lensStrength * 3.0, bezelWidth * 1.25);
    float inset = min(max(-signedDistance, 0.0), bezelWidth);
    float profilePosition = inset / max(bezelWidth, 1.0);
    float profileRemainder = 1.0 - profilePosition;
    float profileHeight = profilePosition * profilePosition
        * (3.0 - 2.0 * profilePosition);
    float profileDerivative = 6.0 * profilePosition * profileRemainder;
    float minSurfaceSize = min(surfaceSize.x, surfaceSize.y);
    vec2 normalizedPosition = surfacePosition / halfSize;
    float domeBase = max(1.0 - 0.72 * dot(normalizedPosition, normalizedPosition), 0.0);
    float domeProfile = domeBase * domeBase;
    vec2 domeGradient = -2.88 * domeBase * normalizedPosition / halfSize;
    float domeDepth = minSurfaceSize * lensStrength * 2.625;
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
    vec2 bezelOffsetPx = refractedRay.xy / rayDepth * slabThickness * fresnelTransmission * rimFade;
    vec2 offsetPx = bezelOffsetPx;
    float maxDisplacementPx = min(max(refractionWidth * 0.8, minSurfaceSize * 0.06),
                                  minSurfaceSize * 0.20);
    float displacementPx = length(offsetPx);
    float limitStartPx = maxDisplacementPx * 0.6;
    float limitBlend = smoothstep(limitStartPx, maxDisplacementPx, displacementPx);
    float limitedDisplacementPx = mix(displacementPx, maxDisplacementPx, limitBlend);
    offsetPx *= limitedDisplacementPx / max(displacementPx, 0.001);
    return clamp(uv + offsetPx / max(backgroundSize, vec2(1.0)), 0.0, 1.0);
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
