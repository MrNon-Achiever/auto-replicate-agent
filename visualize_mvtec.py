from __future__ import annotations

import argparse
import random

import matplotlib.pyplot as plt

import _bootstrap  # noqa: F401
from src.config import load_config, resolve_workspace_path
from src.mvtec import category_samples
from src.visualization import read_mask, read_rgb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save MVTec AD sample visualizations.")
    parser.add_argument("--config", default="configs/project.yaml")
    parser.add_argument("--samples-per-category", type=int, default=4)
    parser.add_argument("--categories", nargs="*", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    data_root = resolve_workspace_path(config, config["data"]["root"])
    output_dir = resolve_workspace_path(config, config["experiment"]["output_dir"]) / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_size = int(config["data"]["image_size"])
    rng = random.Random(int(config["experiment"]["seed"]))

    categories = args.categories if args.categories else config["data"]["categories"]
    for category in categories:
        samples = [sample for sample in category_samples(data_root, category) if sample.split == "test"]
        if not samples:
            print(f"Skip {category}: no test samples found under {data_root / category}")
            continue
        anomaly_samples = [sample for sample in samples if sample.label == 1]
        good_samples = [sample for sample in samples if sample.label == 0]
        chosen = []
        chosen.extend(rng.sample(good_samples, min(1, len(good_samples))))
        chosen.extend(rng.sample(anomaly_samples, min(args.samples_per_category - len(chosen), len(anomaly_samples))))

        fig, axes = plt.subplots(len(chosen), 2, figsize=(6, 3 * len(chosen)))
        if len(chosen) == 1:
            axes = [axes]
        for row_axes, sample in zip(axes, chosen):
            image = read_rgb(sample.path, image_size)
            mask = read_mask(sample.mask_path, image_size)
            row_axes[0].imshow(image)
            row_axes[0].set_title(f"{category}/{sample.defect_type}")
            row_axes[0].axis("off")
            row_axes[1].imshow(mask, cmap="gray")
            row_axes[1].set_title("mask")
            row_axes[1].axis("off")
        fig.tight_layout()
        output_path = output_dir / f"{category}_samples.png"
        fig.savefig(output_path, dpi=180)
        plt.close(fig)
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
