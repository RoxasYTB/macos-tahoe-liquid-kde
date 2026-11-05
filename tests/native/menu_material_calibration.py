#!/usr/bin/env python3
"""Score aligned Tahoe menu captures and fit their measured renderer response.

Manual tool: requires NumPy and Pillow. The 1011x730 reference stays external.
Each TSV row is: capture-name, chroma gain, luma gain, lift (no header).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def load_rgb(path: Path, shape: tuple[int, int] | None = None) -> np.ndarray:
    image = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    if shape:
        height, width = shape
        if image.shape[0] < height or image.shape[1] < width:
            raise ValueError(f"Capture is smaller than the aligned reference: {path}")
        image = image[:height, :width]
    return image


def material_mask(reference: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    if reference.shape[:2] != (730, 1011):
        raise ValueError("Expected the supplied 1011x730 Sort By reference crop")
    mask = np.zeros(reference.shape[:2], dtype=bool)
    mask[176:342, 383:513] = True
    mask[318:558, 551:666] = True
    mask[303:335, 325:540] = False
    mask[398:429, 530:685] = False
    for image in (reference, baseline):
        text = (image.min(axis=2) > 125).astype("uint8") * 255
        expanded = Image.fromarray(text).filter(ImageFilter.MaxFilter(7))
        mask &= np.asarray(expanded) == 0
    for top, bottom, left, right in (
        (190, 203, 330, 537), (269, 283, 330, 537),
        (334, 344, 532, 683), (367, 380, 532, 683),
    ):
        mask[top:bottom, left:right] = False
    return mask


def fit_response(rows: list[dict], target: np.ndarray) -> dict | None:
    design = np.array([row["curve"] + [1.0] for row in rows])
    if len(rows) < 4 or np.linalg.matrix_rank(design) != 4:
        return None
    samples = np.stack([row["sample"].reshape(-1) for row in rows])
    response = np.linalg.lstsq(design, samples, rcond=None)[0]
    curve = np.linalg.lstsq(response[:3].T, target.reshape(-1) - response[3], rcond=None)[0]
    predicted = curve @ response[:3] + response[3]
    return {
        "curve": curve.tolist(),
        "predicted_mae": float(np.abs(predicted - target.reshape(-1)).mean()),
        "response_residual_mae": float(np.abs(design @ response - samples).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reference = load_rgb(args.reference)
    baseline = load_rgb(args.baseline, reference.shape[:2])
    mask = material_mask(reference, baseline)
    target = reference[mask]
    manifest = args.manifest or args.captures / "curves.tsv"
    rows = []
    for line in manifest.read_text().splitlines():
        name, chroma, luma, lift = line.split("\t")
        if Path(name).name != name:
            raise ValueError("Capture names must be basenames")
        sample = load_rgb(args.captures / f"{name}.png", reference.shape[:2])[mask]
        error = np.abs(sample - target)
        rows.append({"name": name, "curve": [float(chroma), float(luma), float(lift)],
                     "mae": float(error.mean()), "rgb_mae": error.mean(axis=0).tolist(),
                     "sample": sample})
    if not rows:
        raise ValueError("No captures in the manifest")
    rows.sort(key=lambda row: row["mae"])
    report = {
        "masked_pixels": int(mask.sum()),
        "baseline_mae": float(np.abs(baseline[mask] - target).mean()),
        "variants": [{key: value for key, value in row.items() if key != "sample"} for row in rows],
        "fit_all": fit_response(rows, target),
        "fit_nearest_nine": fit_response(rows[:9], target),
        "scope": "Material pixels in the aligned crop; not whole-interface fidelity",
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
