// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <QPainterPath>
#include <QImage>
#include <QPainter>
#include <QRegion>
#include <algorithm>
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
