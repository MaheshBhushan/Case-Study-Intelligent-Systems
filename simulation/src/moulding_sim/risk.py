"""Random Forest failure-risk classifier trained on the public AI4I 2020 dataset."""

from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ai4i2020.csv"
MODEL = ROOT / "models" / "risk_rf.joblib"
AI4I_URL = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"
FEATURES = ["Type", "Air temperature [K]", "Process temperature [K]",
            "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]


def engineer(X: np.ndarray) -> np.ndarray:
    """Append physics features: temperature difference [K], power [W], strain [min*Nm]."""
    dt = X[:, 2] - X[:, 1]
    power = X[:, 4] * X[:, 3] * 2 * np.pi / 60
    strain = X[:, 5] * X[:, 4]
    return np.column_stack([X, dt, power, strain])


def fetch_ai4i() -> None:
    """Download AI4I 2020 (CC BY 4.0, Matzka 2020) from the UCI repository if missing."""
    if DATA.exists():
        return
    DATA.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(AI4I_URL) as r, zipfile.ZipFile(io.BytesIO(r.read())) as z:
        DATA.write_bytes(z.read("ai4i2020.csv"))


def load_ai4i() -> tuple[np.ndarray, np.ndarray]:
    fetch_ai4i()
    df = pd.read_csv(DATA)
    df["Type"] = df["Type"].map({"L": 0, "M": 1, "H": 2})
    return engineer(df[FEATURES].to_numpy(float)), df["Machine failure"].to_numpy(int)


def train(seed: int = 0) -> tuple[RandomForestClassifier, dict]:
    X, y = load_ai4i()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=seed)
    rf = RandomForestClassifier(n_estimators=150, min_samples_leaf=2,
                                class_weight="balanced_subsample", random_state=seed)
    rf.fit(Xtr, ytr)
    proba = rf.predict_proba(Xte)[:, 1]
    report = classification_report(yte, proba >= 0.5, output_dict=True, zero_division=0)["1"]
    metrics = {"precision": report["precision"], "recall": report["recall"],
               "f1": report["f1-score"], "roc_auc": roc_auc_score(yte, proba)}
    rf.set_params(n_jobs=1)
    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump(rf, MODEL)
    return rf, metrics


class RiskModel:
    def __init__(self, path: Path = MODEL):
        self.rf = joblib.load(path) if path.exists() else train()[0]
        self._trees = [e.tree_ for e in self.rf.estimators_]

    def predict(self, rows: np.ndarray) -> np.ndarray:
        """rows: raw AI4I feature columns (FEATURES order) -> P(failure).

        Same result as rf.predict_proba, but calls the compiled trees directly: ~50x faster for
        the small batches the simulation sends, because it skips per-call validation overhead.
        """
        X = np.ascontiguousarray(engineer(np.asarray(rows, float)), dtype=np.float32)
        p = np.zeros(len(X))
        for t in self._trees:
            v = t.predict(X)[:, :2]
            p += v[:, 1] / v.sum(axis=1)
        return p / len(self._trees)


if __name__ == "__main__":
    _, m = train()
    print({k: round(v, 3) for k, v in m.items()})
