// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <QPainterPath>
#include <QImage>
#include <QPainter>
#include <QRegion>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <optional>
#include <vector>

inline QRegion integerRoundedRegion(const QRect &bounds, int radius)
{
    QRegion region(bounds.adjusted(radius, 0, -radius, 0));
    region += QRegion(bounds.adjusted(0, radius, 0, -radius));
    for (int x : {bounds.x(), bounds.x() + bounds.width() - 2 * radius}) {
        for (int y : {bounds.y(), bounds.y() + bounds.height() - 2 * radius}) {
            region += QRegion(QRect(x, y, 2 * radius, 2 * radius), QRegion::Ellipse);
        }
    }
    return region;
}

// Recover a rounded popup's curve from its integer blur region. The shader
// can then fade along the curve instead of exposing the region's stair steps.
inline std::optional<float> roundedBlurRadius(const QRegion &region, const QRect &bounds)
{
    if (region.isEmpty() || region.boundingRect() != bounds || bounds.height() < 4) {
        return std::nullopt;
    }
    const QRect firstRow = region.intersected(QRect(bounds.x(), bounds.y(), bounds.width(), 1)).boundingRect();
    const QRect lastRow = region.intersected(QRect(bounds.x(), bounds.bottom(), bounds.width(), 1)).boundingRect();
    const int inset = firstRow.left() - bounds.left();
    if (inset < 1 || std::abs(bounds.right() - firstRow.right() - inset) > 1) {
        return std::nullopt;
    }
    const int estimate = qRound(inset + 0.5 + std::sqrt(inset));
    const int maximum = std::min(bounds.width(), bounds.height()) / 2;
    // Kvantum builds its mask from integer QRegion ellipses. Their first and
    // last scanlines can differ by several pixels, unlike an SVG alpha mask.
    // Match that construction exactly before applying raster-fit tolerances.
    for (int radius = inset; radius <= std::min(maximum, estimate + 3); ++radius) {
        if (integerRoundedRegion(bounds, radius) == region) {
            return float(radius);
        }
    }
    std::optional<float> bestRadius;
    qint64 bestError = std::numeric_limits<qint64>::max();
    // SVG alpha masks include partially covered pixels; thresholded masks
    // round differently. Fit nearby curves instead of trusting one scanline.
    for (int radius = std::max(1, estimate - 2); radius <= std::min(maximum, estimate + 3); ++radius) {
        // Near a capsule's tangent, subpixel rasterization moves the first
        // covered column farther than on a small menu corner.
        const int symmetryTolerance = std::max(1, int(std::ceil(std::sqrt(radius) * 0.5)));
        if (std::abs(lastRow.left() - firstRow.left()) > symmetryTolerance
            || std::abs(lastRow.right() - firstRow.right()) > symmetryTolerance) {
            continue;
        }
        QPainterPath inner, outer;
        // FrameSvg downsamples device-pixel alpha masks to logical pixels.
        // Its SVG arc rasterization can differ from QPainterPath by two
        // pixels, including at 150%, and opposite insets can differ by one.
        inner.addRoundedRect(QRectF(bounds).adjusted(2, 2, -2, -2), std::max(0, radius - 2), std::max(0, radius - 2));
        outer.addRoundedRect(QRectF(bounds).adjusted(-2, -2, 2, 2), radius + 2, radius + 2);
        // Keep holes and custom cutouts outside this rasterization tolerance.
        if (!(QRegion(inner.toFillPolygon().toPolygon()) - region).isEmpty()
            || !(region - QRegion(outer.toFillPolygon().toPolygon())).isEmpty()) {
            continue;
        }
        // A capsule has no straight vertical edge. Prefer its exact
        // half-height curve over a slightly smaller rasterized fit.
        if (radius == maximum) {
            return float(radius);
        }
        // QPainterPath's polygon approximation is too coarse for small menu
        // corners. Compare actual raster coverage, for both alpha-derived SVG
        // masks and thresholded widget masks. Only one corner needs painting.
        QImage corner(radius, radius, QImage::Format_ARGB32_Premultiplied);
        corner.fill(Qt::transparent);
        QPainter painter(&corner);
        painter.setRenderHint(QPainter::Antialiasing);
        painter.setPen(Qt::NoPen);
        painter.setBrush(Qt::white);
        painter.drawRoundedRect(QRectF(0, 0, bounds.width(), bounds.height()), radius, radius);
        painter.end();
        for (int threshold : {1, 128}) {
            QRegion curve(QRect(bounds.x(), bounds.y() + radius, bounds.width(), bounds.height() - 2 * radius));
            for (int y = 0; y < radius; ++y) {
                int x = 0;
                while (x < radius && qAlpha(corner.pixel(x, y)) < threshold) ++x;
                curve += QRect(bounds.x() + x, bounds.y() + y, bounds.width() - 2 * x, 1);
                curve += QRect(bounds.x() + x, bounds.bottom() - y, bounds.width() - 2 * x, 1);
            }
            const QRegion difference = region ^ curve;
            qint64 error = 0;
            for (const QRect &rect : difference) {
                error += qint64(rect.width()) * rect.height();
            }
            if (error < bestError) {
                bestRadius = radius;
                bestError = error;
            }
        }
    }
    return bestRadius;
}

struct ClientBlurShape
{
    QRect bounds;
    float radius;
    bool integerEllipse = false;
    float squircleBlend = 0.0f;

    // Integer ellipse masks clip partial coverage asymmetrically. Keep the
    // antialiasing ramp inside their region, beneath the client's SVG edge.
    // Alpha-derived Plasma masks already include that coverage.
    QRectF surfaceRect() const
    {
        return integerEllipse ? QRectF(bounds).adjusted(1, 1, -1, -1) : QRectF(bounds);
    }
    float cornerRadius() const
    {
        return integerEllipse ? std::max(0.0f, radius - 1.0f) : radius;
    }
};

// Fit the rounded/superelliptic profile used by a single client glass card.
// The app publishes only an alpha-derived blur region, so recover both its
// corner radius and its circle-to-squircle blend from the actual mask.
inline std::optional<ClientBlurShape> fitClientBlurShape(const QRegion &region)
{
    if (region.isEmpty()) return std::nullopt;
    const QRect bounds = region.boundingRect();
    if (region == QRegion(bounds)) return ClientBlurShape{bounds, 0.0f};
    if (bounds.height() < 4 || bounds.width() < 4) return std::nullopt;

    const QRect first = region.intersected(QRect(bounds.x(), bounds.y(), bounds.width(), 1)).boundingRect();
    if (first.isEmpty()) return std::nullopt;
    const int inset = std::max(0, first.left() - bounds.left());
    const int estimate = qRound(inset + 0.5 + std::sqrt(inset));
    const int maximum = std::min(bounds.width(), bounds.height()) / 2;
    const int radiusStart = std::max(1, estimate - 8);
    const int radiusEnd = std::min(maximum, estimate + 8);
    constexpr float blends[] = {0.0f, 0.125f, 0.25f, 0.375f, 0.5f, 0.625f, 0.75f, 0.875f, 1.0f};
    qint64 bestError = std::numeric_limits<qint64>::max();
    int bestRadius = 0;
    float bestBlend = 0.0f;
    const float halfWidth = bounds.width() * 0.5f;
    const float halfHeight = bounds.height() * 0.5f;

    // QRegion::contains() is expensive for alpha masks with hundreds of
    // scanline rectangles. Rasterize once so the candidate fit remains cheap
    // even when the client publishes a supersampled SVG mask.
    std::vector<uchar> coverage(size_t(bounds.width()) * size_t(bounds.height()), 0);
    for (const QRect &rect : region) {
        const QRect local = rect.translated(-bounds.topLeft());
        for (int y = local.top(); y <= local.bottom(); ++y) {
            std::fill_n(coverage.data() + size_t(y) * size_t(bounds.width()) + size_t(local.left()),
                        size_t(local.width()), uchar(1));
        }
    }

    // Every candidate is guaranteed to cover the central cross of the
    // bounds. Compare that part once, then evaluate only the four corner
    // patches where radius and squircle exponent can change coverage. The
    // previous full-image scan ran hypot()/pow() for every pixel and every
    // candidate; this keeps the expensive fit proportional to r^2 instead
    // of the whole card area.
    qint64 centralError = 0;
    const float centralX = halfWidth - radiusEnd;
    const float centralY = halfHeight - radiusEnd;
    for (int y = 0; y < bounds.height(); ++y) {
        const float py = std::abs((y + 0.5f) - halfHeight);
        for (int x = 0; x < bounds.width(); ++x) {
            const float px = std::abs((x + 0.5f) - halfWidth);
            if (px <= centralX || py <= centralY) {
                if (coverage[size_t(y) * size_t(bounds.width()) + size_t(x)] == 0) {
                    ++centralError;
                }
            }
        }
    }
    const int cornerWidth = std::min(bounds.width(), radiusEnd);
    const int cornerHeight = std::min(bounds.height(), radiusEnd);
    constexpr size_t blendCount = sizeof(blends) / sizeof(blends[0]);
    for (int radius = radiusStart; radius <= radiusEnd; ++radius) {
        std::array<qint64, blendCount> errors;
        errors.fill(centralError);
        for (int cornerY = 0; cornerY < 2; ++cornerY) {
            const int yStart = cornerY == 0 ? 0 : bounds.height() - cornerHeight;
            const int yEnd = cornerY == 0 ? cornerHeight : bounds.height();
            for (int y = yStart; y < yEnd; ++y) {
                const float py = std::abs((y + 0.5f) - halfHeight);
                for (int cornerX = 0; cornerX < 2; ++cornerX) {
                    const int xStart = cornerX == 0 ? 0 : bounds.width() - cornerWidth;
                    const int xEnd = cornerX == 0 ? cornerWidth : bounds.width();
                    for (int x = xStart; x < xEnd; ++x) {
                        const float px = std::abs((x + 0.5f) - halfWidth);
                        if (px <= centralX || py <= centralY) continue;
                        const float qx = px - halfWidth + radius;
                        const float qy = py - halfHeight + radius;
                        const float outsideX = std::max(qx, 0.0f);
                        const float outsideY = std::max(qy, 0.0f);
                        const float base = std::min(std::max(qx, qy), 0.0f) - radius;
                        const float circular = std::hypot(outsideX, outsideY);
                        const float superelliptic = std::pow(std::pow(outsideX, 4.0f) + std::pow(outsideY, 4.0f), 0.25f);
                        const bool covered = coverage[size_t(y) * size_t(bounds.width()) + size_t(x)] != 0;
                        for (size_t blend = 0; blend < blendCount; ++blend) {
                            const float distance = base + circular * (1.0f - blends[blend])
                                + superelliptic * blends[blend];
                            if ((distance <= 0.0f) != covered) ++errors[blend];
                        }
                    }
                }
            }
        }
        for (size_t blend = 0; blend < blendCount; ++blend) {
            if (errors[blend] < bestError) {
                bestError = errors[blend];
                bestRadius = radius;
                bestBlend = blends[blend];
            }
        }
    }
    const qint64 area = qint64(bounds.width()) * bounds.height();
    if (bestRadius == 0 || bestError > area / 12) return std::nullopt;
    return ClientBlurShape{bounds, float(bestRadius), false, bestBlend};
}

inline std::optional<ClientBlurShape> clientBlurShape(const QRegion &region)
{
    if (region.isEmpty()) {
        return std::nullopt;
    }
    const QRect bounds = region.boundingRect();
    if (region == QRegion(bounds)) {
        return ClientBlurShape{bounds, 0.0f};
    }
    if (const auto radius = roundedBlurRadius(region, bounds)) {
        return ClientBlurShape{bounds, *radius, integerRoundedRegion(bounds, qRound(*radius)) == region};
    }
    return std::nullopt;
}

// Two adjacent circular controls can touch at one antialiased pixel and
// become a single connected QRegion component. Recover that narrow case by
// testing balanced cuts near the midpoint, and accept a cut only when both
// sides independently fit near-circular shapes.
inline std::optional<std::array<ClientBlurShape, 2>> splitTangentRoundShapes(const QRegion &component)
{
    const QRect bounds = component.boundingRect();
    if (bounds.width() < bounds.height() * 3 / 2 || bounds.height() < 12) return std::nullopt;

    const int halfWidth = bounds.height() / 2;
    const int midpoint = bounds.center().x();
    const int search = std::max(1, bounds.height() / 4);
    float bestScore = std::numeric_limits<float>::max();
    std::optional<std::array<ClientBlurShape, 2>> best;

    for (int cut = midpoint - search; cut <= midpoint + search; ++cut) {
        if (cut < bounds.left() + 4 || cut >= bounds.right() - 4) continue;
        const QRegion left = component.intersected(QRect(bounds.left(), bounds.top(), cut - bounds.left() + 1, bounds.height()));
        const QRegion right = component.intersected(QRect(cut + 1, bounds.top(), bounds.right() - cut, bounds.height()));
        const auto leftShape = fitClientBlurShape(left);
        const auto rightShape = fitClientBlurShape(right);
        if (!leftShape || !rightShape) continue;

        const auto roundError = [halfWidth](const ClientBlurShape &shape) {
            const int width = shape.bounds.width();
            const int height = shape.bounds.height();
            const float aspectError = float(std::abs(width - height)) / std::max(width, height);
            const float radiusError = std::abs(shape.radius - halfWidth) / std::max(halfWidth, 1);
            if (aspectError > 0.12f || radiusError > 0.18f) return std::numeric_limits<float>::max();
            return aspectError + radiusError;
        };
        const float leftError = roundError(*leftShape);
        const float rightError = roundError(*rightShape);
        if (!std::isfinite(leftError) || !std::isfinite(rightError)) continue;

        const float score = leftError + rightError;
        if (score < bestScore) {
            bestScore = score;
            best = std::array<ClientBlurShape, 2>{*leftShape, *rightShape};
        }
    }
    return best;
}

// Split a client blur region into connected surfaces. Control panels often
// publish several independent Liquid Glass cards through one X11 blur region;
// treating their bounding box as a single rounded rectangle produces false
// optical normals across the gaps between cards.
inline std::vector<ClientBlurShape> clientBlurShapes(const QRegion &region)
{
    std::vector<QRect> rects;
    rects.reserve(size_t(region.rectCount()));
    for (const QRect &rect : region) rects.push_back(rect);
    std::vector<uchar> visited(rects.size(), 0);
    std::vector<ClientBlurShape> shapes;
    std::vector<size_t> queue;
    for (size_t seed = 0; seed < rects.size(); ++seed) {
        if (visited[seed]) continue;
        queue.clear();
        queue.push_back(seed);
        visited[seed] = 1;
        QRegion component;
        for (size_t i = 0; i < queue.size(); ++i) {
            const QRect current = rects[queue[i]];
            component += current;
            for (size_t j = 0; j < rects.size(); ++j) {
                if (visited[j]) continue;
                if (current.adjusted(-1, -1, 1, 1).intersects(rects[j])) {
                    visited[j] = 1;
                    queue.push_back(j);
                }
            }
        }
        if (const auto shape = fitClientBlurShape(component)) {
            shapes.push_back(*shape);
            continue;
        }
        if (const auto pair = splitTangentRoundShapes(component)) {
            shapes.insert(shapes.end(), pair->begin(), pair->end());
            continue;
        }
        const QRect bounds = component.boundingRect();
        if (bounds.isEmpty() || bounds.height() < 4) return {};
        const QRect first = component.intersected(QRect(bounds.x(), bounds.y(), bounds.width(), 1)).boundingRect();
        const QRect last = component.intersected(QRect(bounds.x(), bounds.bottom(), bounds.width(), 1)).boundingRect();
        if (first.isEmpty() || last.isEmpty()) return {};
        const int inset = std::max(0, first.left() - bounds.left());
        const int estimate = qRound(inset + 0.5 + std::sqrt(inset));
        const int maximum = std::min(bounds.width(), bounds.height()) / 2;
        const int tolerance = std::max(4, int(std::ceil(std::sqrt(std::max(estimate, 1)) * 0.5)));
        if (std::abs(bounds.right() - first.right() - inset) > tolerance
            || std::abs(last.left() - first.left()) > tolerance
            || std::abs(last.right() - first.right()) > tolerance) return {};
        // FrameSvg uses superelliptical (squircle) masks. Fit their top inset
        // to the nearest rounded-rect radius. Wide capsules use their exact
        // half-height, while near-square cards use the squircle inset fit.
        const int radius = bounds.width() >= bounds.height() * 3 / 2
            ? bounds.height() / 2
            : std::clamp(estimate, 0, maximum);
        shapes.push_back(ClientBlurShape{bounds, float(radius), false});
    }
    return shapes;
}

// Build a per-pixel blur weight for the window's blur region. The blur stays
// sharp at the glass edge and reaches full strength over a short inward
// distance, avoiding a hard transition between blurred and crisp backdrop.
inline QImage blurFalloffMask(const QRegion &region, int fadePixels = 6)
{
    const QRect bounds = region.boundingRect();
    if (bounds.isEmpty()) {
        return {};
    }

    QImage mask(bounds.size(), QImage::Format_RGBA8888);
    if (mask.isNull()) {
        return {};
    }
    mask.fill(0);

    QPainter painter(&mask);
    painter.setPen(Qt::white);
    painter.setBrush(Qt::white);
    for (const QRect &rect : region) {
        painter.drawRect(rect.translated(-bounds.topLeft()));
    }
    painter.end();

    const int width = mask.width();
    const int height = mask.height();
    const int unreachable = std::max(1, fadePixels + 1);
    std::vector<int> distance(size_t(width) * size_t(height), unreachable);
    auto inside = [&mask](int x, int y) {
        return mask.constScanLine(y)[x * 4 + 3] != 0;
    };
    auto index = [width](int x, int y) {
        return size_t(y) * size_t(width) + size_t(x);
    };

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (inside(x, y)) {
                if (x == 0 || y == 0 || x == width - 1 || y == height - 1) {
                    distance[index(x, y)] = 1;
                }
                continue;
            }
            const size_t i = index(x, y);
            distance[i] = 0;
            if (x > 0 && inside(x - 1, y)) distance[index(x - 1, y)] = 1;
            if (y > 0 && inside(x, y - 1)) distance[index(x, y - 1)] = 1;
        }
    }

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (!inside(x, y)) continue;
            int &d = distance[index(x, y)];
            if (x > 0) d = std::min(d, distance[index(x - 1, y)] + 1);
            if (y > 0) d = std::min(d, distance[index(x, y - 1)] + 1);
        }
    }
    for (int y = height - 1; y >= 0; --y) {
        for (int x = width - 1; x >= 0; --x) {
            if (!inside(x, y)) continue;
            int &d = distance[index(x, y)];
            if (x + 1 < width) d = std::min(d, distance[index(x + 1, y)] + 1);
            if (y + 1 < height) d = std::min(d, distance[index(x, y + 1)] + 1);
        }
    }

    for (int y = 0; y < height; ++y) {
        auto *row = mask.scanLine(y);
        for (int x = 0; x < width; ++x) {
            const float t = std::clamp(float(distance[index(x, y)]) / float(std::max(1, fadePixels)), 0.0f, 1.0f);
            const float smooth = t * t * (3.0f - 2.0f * t);
            const uchar value = inside(x, y) ? uchar(std::lround(smooth * 255.0f)) : 0;
            row[x * 4 + 0] = value;
            row[x * 4 + 1] = value;
            row[x * 4 + 2] = value;
            row[x * 4 + 3] = value;
        }
    }
    return mask;
}
