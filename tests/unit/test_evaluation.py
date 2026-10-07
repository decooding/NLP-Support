from support_dispatcher.evaluation.metrics import (
    compute_ece,
    compute_macro_f1,
    compute_selective_metrics,
)


def test_compute_macro_f1():
    y_true = ["SED", "DKA", "TECHNICAL_BUG"]
    y_pred = ["SED", "DKA", "TECHNICAL_BUG"]
    classes = ["SED", "DKA", "TECHNICAL_BUG"]
    f1 = compute_macro_f1(y_true, y_pred, classes)
    assert f1 == 1.0

    y_pred_bad = ["TECHNICAL_BUG", "SED", "DKA"]
    f1_bad = compute_macro_f1(y_true, y_pred_bad, classes)
    assert f1_bad == 0.0


def test_compute_ece():
    confidences = [0.9, 0.8, 0.6, 0.4]
    accuracies = [True, True, False, False]
    ece = compute_ece(confidences, accuracies, num_bins=5)
    assert 0.0 <= ece <= 1.0


def test_compute_selective_metrics():
    y_true = ["SED", "SED", "DKA", "DKA"]
    y_pred = ["SED", "DKA", "DKA", "DKA"]
    confidences = [0.95, 0.60, 0.90, 0.88]

    metrics = compute_selective_metrics(y_true, y_pred, confidences, threshold=0.85)
    assert metrics["coverage"] == 0.75  # 3 out of 4 accepted
    assert metrics["fallback_rate"] == 0.25
    assert metrics["selective_accuracy"] == 1.0  # All accepted are correct
