import argparse
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


AI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = AI_ROOT / "data" / "intent_dataset.jsonl"
DEFAULT_MODEL_OUT = AI_ROOT / "data" / "intent_model.joblib"
DEFAULT_METRICS_OUT = AI_ROOT / "data" / "intent_metrics.json"



def read_jsonl(path: Path):
    samples = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            row = json.loads(raw)
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip()
            if text and label:
                samples.append((text, label))
    return samples



def main():
    parser = argparse.ArgumentParser(description="Train intent classifier for Studify AI")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_OUT)
    parser.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS_OUT)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--min-confidence", type=float, default=0.45)
    args = parser.parse_args()

    dataset_path = args.dataset if args.dataset.is_absolute() else (AI_ROOT / args.dataset)
    model_out_path = args.model_out if args.model_out.is_absolute() else (AI_ROOT / args.model_out)
    metrics_out_path = args.metrics_out if args.metrics_out.is_absolute() else (AI_ROOT / args.metrics_out)

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy dataset: {dataset_path}. "
            f"Hãy kiểm tra file data/intent_dataset.jsonl hoặc truyền --dataset đúng đường dẫn."
        )

    samples = read_jsonl(dataset_path)
    if len(samples) < 12:
        raise ValueError("Dataset quá nhỏ. Cần ít nhất 12 mẫu để train ổn định.")

    texts = [item[0] for item in samples]
    labels = [item[1] for item in samples]

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=args.test_size,
        random_state=42,
        stratify=labels,
    )

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    max_features=6000,
                    min_df=1,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1500,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )

    pipeline.fit(x_train, y_train)

    y_pred = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_out_path.parent.mkdir(parents=True, exist_ok=True)

    artifact = {
        "pipeline": pipeline,
        "labels": sorted(list(set(labels))),
        "min_confidence": float(args.min_confidence),
        "dataset_size": len(samples),
    }
    joblib.dump(artifact, model_out_path)

    metrics = {
        "accuracy": accuracy,
        "report": report,
        "dataset_size": len(samples),
        "test_size": args.test_size,
        "model_file": str(model_out_path),
    }
    with metrics_out_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)

    print(f"Train xong. Accuracy={accuracy:.4f}")
    print(f"Model: {model_out_path}")
    print(f"Metrics: {metrics_out_path}")


if __name__ == "__main__":
    main()
