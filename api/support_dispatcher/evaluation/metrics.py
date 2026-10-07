"""Metrics and evaluation utilities for System 1 & System 2 according to DoD."""

from __future__ import annotations

from collections.abc import Sequence


def compute_macro_f1(y_true: Sequence[str], y_pred: Sequence[str], classes: Sequence[str]) -> float:
    """Computes unweighted mean of F1 scores across all unique classes."""
    if not y_true or not y_pred:
        return 0.0

    f1_list: list[float] = []
    for cls in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp == cls)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != cls and yp == cls)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        f1_list.append(f1)

    return sum(f1_list) / len(f1_list) if f1_list else 0.0


def compute_ece(
    confidences: Sequence[float],
    accuracies: Sequence[bool],
    num_bins: int = 10,
) -> float:
    """Computes Expected Calibration Error (ECE)."""
    if not confidences or not accuracies:
        return 0.0

    n = len(confidences)
    bin_boundaries = [i / num_bins for i in range(num_bins + 1)]
    ece = 0.0

    for i in range(num_bins):
        low, high = bin_boundaries[i], bin_boundaries[i + 1]
        bin_indices = [
            idx
            for idx, c in enumerate(confidences)
            if (low <= c < high or (i == num_bins - 1 and low <= c <= high))
        ]

        if not bin_indices:
            continue

        bin_conf = sum(confidences[idx] for idx in bin_indices) / len(bin_indices)
        bin_acc = sum(1.0 for idx in bin_indices if accuracies[idx]) / len(bin_indices)

        ece += (len(bin_indices) / n) * abs(bin_acc - bin_conf)

    return ece


def compute_selective_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    confidences: Sequence[float],
    threshold: float,
) -> dict[str, float]:
    """Computes Coverage, Selective Accuracy, and System 2 Fallback Rate at a given threshold."""
    total = len(y_true)
    if total == 0:
        return {"coverage": 0.0, "selective_accuracy": 0.0, "fallback_rate": 0.0}

    accepted_indices = [i for i, c in enumerate(confidences) if c >= threshold]
    accepted_count = len(accepted_indices)

    coverage = accepted_count / total
    fallback_rate = 1.0 - coverage

    if accepted_count > 0:
        correct_accepted = sum(1 for i in accepted_indices if y_true[i] == y_pred[i])
        selective_acc = correct_accepted / accepted_count
    else:
        selective_acc = 1.0

    return {
        "coverage": round(coverage, 4),
        "selective_accuracy": round(selective_acc, 4),
        "fallback_rate": round(fallback_rate, 4),
    }
