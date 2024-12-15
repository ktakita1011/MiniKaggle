from typing import List

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


def classification_metrics(y_true, y_pred):
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1_score": f1_score(y_true, y_pred),
    }
    return metrics["accuracy"]


def calc_metric(y_pred: List[float]) -> float:
    target_col = "Survived"
    test = pd.read_csv("../data/competition/test.csv")
    y_true = test[target_col].tolist()
    metric_score = classification_metrics(y_true, y_pred)
    return metric_score
