#!/usr/bin/env python3
"""
Compute accuracy metrics comparing model predictions vs. human GT labels.

Usage:
    python compute_accuracy.py \
        --pred_dir <path_to_predictions> \
        --label_dir <path_to_labels> \
        [--output <report.json>]
"""

import argparse
import json
import os
from pathlib import Path
from collections import defaultdict


DIMENSIONS = [
    "visual_quality",
    "text_to_video_alignment",
    "physical_common_sense_consisitency",
]

DIM_SHORT = {
    "visual_quality": "VQ",
    "text_to_video_alignment": "T2V",
    "physical_common_sense_consisitency": "PHY",
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def compute_metrics(pred_dir, label_dir):
    pred_dir = Path(pred_dir)
    label_dir = Path(label_dir)

    # Find all prediction files
    pred_files = sorted(pred_dir.glob("*.json"))
    if not pred_files:
        raise FileNotFoundError(f"No JSON files found in {pred_dir}")

    records = []
    skipped = []

    for pred_path in pred_files:
        video_name = pred_path.stem
        label_path = label_dir / f"{video_name}_label.json"

        if not label_path.exists():
            skipped.append(video_name)
            continue

        pred = load_json(pred_path)
        gt = load_json(label_path)

        record = {"video": video_name}
        for dim in DIMENSIONS:
            p = pred.get(dim)
            g = gt.get(dim)
            if p is None or g is None:
                continue
            record[f"pred_{dim}"] = int(p)
            record[f"gt_{dim}"] = int(g)
            record[f"diff_{dim}"] = int(p) - int(g)

        records.append(record)

    if not records:
        raise ValueError("No matching prediction/label pairs found.")

    n = len(records)
    results = {"n_videos": n, "skipped": skipped, "dimensions": {}, "overall": {}}

    all_exact = []
    all_within1 = []
    all_abs_err = []

    for dim in DIMENSIONS:
        key = f"diff_{dim}"
        diffs = [r[key] for r in records if key in r]
        exact = [1 if d == 0 else 0 for d in diffs]
        within1 = [1 if abs(d) <= 1 else 0 for d in diffs]
        abs_err = [abs(d) for d in diffs]

        # Per-score breakdown
        score_dist = defaultdict(lambda: {"pred": 0, "gt": 0})
        for r in records:
            if f"pred_{dim}" in r:
                score_dist[r[f"pred_{dim}"]]["pred"] += 1
            if f"gt_{dim}" in r:
                score_dist[r[f"gt_{dim}"]]["gt"] += 1

        results["dimensions"][dim] = {
            "exact_match_acc": round(sum(exact) / len(exact), 4) if exact else 0,
            "within1_acc": round(sum(within1) / len(within1), 4) if within1 else 0,
            "mae": round(sum(abs_err) / len(abs_err), 4) if abs_err else 0,
            "mean_pred": round(sum(r[f"pred_{dim}"] for r in records if f"pred_{dim}" in r) / n, 3),
            "mean_gt": round(sum(r[f"gt_{dim}"] for r in records if f"gt_{dim}" in r) / n, 3),
            "bias": round(
                sum(r[f"diff_{dim}"] for r in records if f"diff_{dim}" in r) / n, 3
            ),  # positive = model overestimates
            "score_distribution": {k: dict(v) for k, v in sorted(score_dist.items())},
        }

        all_exact.extend(exact)
        all_within1.extend(within1)
        all_abs_err.extend(abs_err)

        # Per-video details
        results["dimensions"][dim]["per_video"] = [
            {
                "video": r["video"],
                "pred": r.get(f"pred_{dim}"),
                "gt": r.get(f"gt_{dim}"),
                "diff": r.get(f"diff_{dim}"),
            }
            for r in records
            if f"pred_{dim}" in r
        ]

    results["overall"] = {
        "exact_match_acc": round(sum(all_exact) / len(all_exact), 4),
        "within1_acc": round(sum(all_within1) / len(all_within1), 4),
        "mae": round(sum(all_abs_err) / len(all_abs_err), 4),
    }

    return results


def print_report(results):
    print("=" * 60)
    print(f"VIDEO EVALUATION ACCURACY REPORT  (n={results['n_videos']} videos)")
    print("=" * 60)

    print("\n[OVERALL]")
    o = results["overall"]
    print(f"  Exact Match Accuracy : {o['exact_match_acc']*100:.1f}%")
    print(f"  Within-±1 Accuracy   : {o['within1_acc']*100:.1f}%")
    print(f"  Mean Absolute Error  : {o['mae']:.3f}")

    print("\n[PER DIMENSION]")
    header = f"  {'Dimension':<35} {'Exact':>6} {'±1':>6} {'MAE':>6} {'Bias':>7} {'MeanPred':>9} {'MeanGT':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for dim in DIMENSIONS:
        d = results["dimensions"][dim]
        print(
            f"  {dim:<35} {d['exact_match_acc']*100:>5.1f}% {d['within1_acc']*100:>5.1f}% "
            f"{d['mae']:>6.3f} {d['bias']:>+7.3f} {d['mean_pred']:>9.3f} {d['mean_gt']:>7.3f}"
        )

    print("\n[ERROR ANALYSIS — largest misses per dimension]")
    for dim in DIMENSIONS:
        d = results["dimensions"][dim]
        big_errors = sorted(
            d["per_video"], key=lambda x: abs(x["diff"]) if x["diff"] is not None else 0, reverse=True
        )[:5]
        print(f"\n  {dim}:")
        for e in big_errors:
            direction = "↑over" if e["diff"] > 0 else "↓under"
            print(f"    {e['video']:20s}  pred={e['pred']}  gt={e['gt']}  diff={e['diff']:+d} ({direction})")

    if results["skipped"]:
        print(f"\n[SKIPPED] {len(results['skipped'])} videos (no GT label found):")
        for v in results["skipped"]:
            print(f"  {v}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Compute video eval accuracy vs. GT labels")
    parser.add_argument("--pred_dir", required=True, help="Directory containing prediction JSON files")
    parser.add_argument("--label_dir", required=True, help="Directory containing GT label JSON files")
    parser.add_argument("--output", default=None, help="Optional path to save full report JSON")
    args = parser.parse_args()

    results = compute_metrics(args.pred_dir, args.label_dir)
    print_report(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nFull report saved to: {args.output}")


if __name__ == "__main__":
    main()
