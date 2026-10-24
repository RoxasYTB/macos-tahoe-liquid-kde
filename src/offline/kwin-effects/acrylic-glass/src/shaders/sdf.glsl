// MacTahoe Liquid KDE — Acrylic Glass SDF helpers

#ifndef LIQUIDGLASS_SDF_GLSL
#define LIQUIDGLASS_SDF_GLSL

uniform vec2 blurSize;
uniform float cornerSquircle;

// Match ShapeCorners' circle/superellipse blend at the window boundary.
float lgCornerLength(vec2 q)
{
    float circle = length(q);
    float squircle = pow(dot(q * q, q * q), 0.25);
    return mix(circle, squircle, cornerSquircle);
}

float lgRoundedRectDistance(vec2 p, vec2 halfSize, vec4 cornerRadius)
{
    float r = p.x > 0.0
        ? (p.y > 0.0 ? cornerRadius.y : cornerRadius.w)
        : (p.y > 0.0 ? cornerRadius.x : cornerRadius.z);
    vec2 q = abs(p) - halfSize + r;
    return min(max(q.x, q.y), 0.0) + lgCornerLength(max(q, 0.0)) - r;
}

float lgRoundedRectCoverage(float distance)
{
    // Geometry is in device pixels. Cover the first interior pixel fully;
    // a wider inward fade exposes the untinted wallpaper as a bright rim.
    float pixelWidth = max(fwidth(distance), 1.0);
    return 1.0 - smoothstep(-0.5 * pixelWidth, 0.5 * pixelWidth, distance);
}

vec2 lgRoundedRectNormal(vec2 p, vec2 halfSize, vec4 cornerRadius, float squircleBlend)
{
    float r = p.x > 0.0
        ? (p.y > 0.0 ? cornerRadius.y : cornerRadius.w)
        : (p.y > 0.0 ? cornerRadius.x : cornerRadius.z);
    vec2 q = abs(p) - halfSize + r;
    vec2 qc = max(q, 0.0);
    float ql = length(qc);
    vec2 cornerNormal = vec2(0.0, 1.0);
    if (ql > 0.001) {
        float q4 = dot(qc * qc, qc * qc);
        vec2 circleGradient = qc / ql;
        vec2 squircleGradient = vec2(qc.x * qc.x * qc.x, qc.y * qc.y * qc.y)
            / max(pow(q4, 0.75), 0.001);
        cornerNormal = normalize(mix(circleGradient, squircleGradient, clamp(squircleBlend, 0.0, 1.0)));
    }
    float axisBlendWidth = max(min(r * 0.75, 24.0), 1.0);
    float axisBlend = smoothstep(-axisBlendWidth, axisBlendWidth, q.x - q.y);
    vec2 axisNormal = normalize(mix(vec2(0.0, 1.0), vec2(1.0, 0.0), axisBlend));
    vec2 n = (ql > 0.001) ? cornerNormal : axisNormal;
    return n * sign(p + 0.0001);
}

#endif
