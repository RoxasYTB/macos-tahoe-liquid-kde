// MacTahoe Liquid KDE — Acrylic Glass highlight helpers

#ifndef LIQUIDGLASS_HIGHLIGHT_GLSL
#define LIQUIDGLASS_HIGHLIGHT_GLSL

// Frame-local coordinates grow downwards, independently of texture orientation.
// A thin upper highlight defines the glass edge without a broad painted rim.
float lgRimAngularWeight(vec2 outNorm)
{
    return 0.65 + 0.55 * clamp(-outNorm.y * 0.5 + 0.5, 0.0, 1.0);
}

vec3 lgApplyHighlight(vec3 color, float inside, vec2 outNorm,
                      float highlightWidth, float highlightStrength, bool dockSurface)
{
    float band = max(highlightWidth, 1.0);
    // The Dock catches light at the silhouette; keep the reflection within
    // the pixel-scaled band instead of fading it out at the glass edge.
    float rim = dockSurface
        ? 1.6 * exp(-inside * (2.0 / band))
        : exp(-inside * (3.0 / band)) * smoothstep(0.0, 2.0, inside);
    float intensity = rim * highlightStrength * lgRimAngularWeight(outNorm);
    return mix(color, vec3(0.87, 0.93, 1.0), clamp(intensity, 0.0, 0.95));
}

vec3 lgApplyLensReflection(vec3 color, vec3 surfaceNormal, float strength)
{
    vec3 viewDirection = vec3(0.0, 0.0, 1.0);
    vec3 lightDirection = normalize(vec3(-0.45, -0.55, 1.4));
    vec3 halfDirection = normalize(lightDirection + viewDirection);
    float normalView = clamp(dot(surfaceNormal, viewDirection), 0.0, 1.0);
    float fresnelBase = 1.0 - normalView;
    float fresnelSquare = fresnelBase * fresnelBase;
    float fresnel = 0.035 + 0.965 * fresnelSquare * fresnelSquare * fresnelBase;
    float specularBase = max(dot(surfaceNormal, halfDirection), 0.0);
    float specularSquare = specularBase * specularBase;
    float specularFourth = specularSquare * specularSquare;
    float specularEighth = specularFourth * specularFourth;
    float specularSixteenth = specularEighth * specularEighth;
    float specularThirtySecond = specularSixteenth * specularSixteenth;
    float specular = specularThirtySecond * specularThirtySecond;
    vec3 environmentTint = mix(vec3(0.72, 0.86, 1.0), clamp(color, 0.0, 1.0), 0.65);
    vec3 reflectedLight = environmentTint * (0.30 * fresnel + 2.0 * specular);
    return color + reflectedLight * strength;
}

#endif
