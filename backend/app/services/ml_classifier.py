import os
import re
import joblib
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
from app.config import MODELS_DIR, DATA_DIR, STANDARD_CATEGORIES

class MLClassifier:
    """Traditional Supervised Machine Learning Classifier for transaction descriptions using TF-IDF and Multinomial Naive Bayes."""

    def __init__(self):
        self.model_path = MODELS_DIR / "classifier_model.joblib"
        self.vectorizer_path = MODELS_DIR / "tfidf_vectorizer.joblib"
        self.model: Optional[MultinomialNB] = None
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.is_trained = False
        self.classes_: List[str] = []
        self.evaluation_cache: Optional[Dict[str, Any]] = None
        self.load_model()

    @staticmethod
    def clean_text(text: str) -> str:
        """Preprocesses transaction description text: lowercasing, removing special characters/numbers while keeping alphabetic tokens."""
        if not text:
            return ""
        t = text.lower()
        t = re.sub(r'[^a-z0-9\s]', ' ', t)
        t = re.sub(r'\s+', ' ', t)
        return t.strip()

    def train(self, data_path: Optional[str] = None) -> Dict[str, Any]:
        """Trains the TF-IDF and Multinomial Naive Bayes classifier on labelled transaction descriptions."""
        csv_file = data_path or str(DATA_DIR / "training_data.csv")
        if not os.path.exists(csv_file):
            return {
                "success": False,
                "error": f"Training dataset not found at {csv_file}. Supervised ML model requires labelled training data."
            }

        df = pd.read_csv(csv_file)
        if "description" not in df.columns or "category" not in df.columns:
            return {
                "success": False,
                "error": "Dataset must contain 'description' and 'category' columns."
            }

        df = df.dropna(subset=["description", "category"])
        X_raw = df["description"].tolist()
        y = df["category"].tolist()

        X_clean = [self.clean_text(x) for x in X_raw]

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            token_pattern=r'(?u)\b\w+\b'
        )
        X_vec = vectorizer.fit_transform(X_clean)

        model = MultinomialNB(alpha=0.2)
        model.fit(X_vec, y)

        self.model = model
        self.vectorizer = vectorizer
        self.is_trained = True
        self.classes_ = list(model.classes_)

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, self.model_path)
        joblib.dump(vectorizer, self.vectorizer_path)

        return {
            "success": True,
            "sample_count": len(df),
            "classes": self.classes_,
            "vocabulary_size": len(vectorizer.vocabulary_)
        }

    def evaluate_model(self, data_path: Optional[str] = None, test_size: float = 0.25, random_state: int = 42) -> Dict[str, Any]:
        """
        Evaluates the TF-IDF + Multinomial Naive Bayes model on a strictly held-out test split.
        Generates Accuracy, Precision, Recall, F1-score, Confusion Matrix, and Sample Counts per Category.
        """
        csv_file = data_path or str(DATA_DIR / "training_data.csv")
        if not os.path.exists(csv_file):
            return {"success": False, "error": "Evaluation dataset not found"}

        df = pd.read_csv(csv_file).dropna(subset=["description", "category"])
        X_clean = [self.clean_text(x) for x in df["description"].tolist()]
        y = df["category"].tolist()

        # Check if all classes have at least 2 samples for stratified split
        class_counts = pd.Series(y).value_counts()
        can_stratify = class_counts.min() >= 2
        stratify_arg = y if can_stratify else None

        X_train, X_test, y_train, y_test = train_test_split(
            X_clean, y, test_size=test_size, random_state=random_state, stratify=stratify_arg
        )

        eval_vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, token_pattern=r'(?u)\b\w+\b')
        X_train_vec = eval_vec.fit_transform(X_train)
        X_test_vec = eval_vec.transform(X_test)

        eval_model = MultinomialNB(alpha=0.2)
        eval_model.fit(X_train_vec, y_train)

        y_pred = eval_model.predict(X_test_vec)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        rec = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

        labels = sorted(list(set(y_test) | set(y_pred)))
        cm = confusion_matrix(y_test, y_pred, labels=labels).tolist()

        # Calculate per-category sample counts and metrics
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        samples_per_category = {}
        for cat in labels:
            test_cnt = int(pd.Series(y_test).value_counts().get(cat, 0))
            train_cnt = int(pd.Series(y_train).value_counts().get(cat, 0))
            cat_rep = report.get(cat, {})
            samples_per_category[cat] = {
                "test_samples": test_cnt,
                "train_samples": train_cnt,
                "total_samples": test_cnt + train_cnt,
                "precision": round(cat_rep.get("precision", 0.0), 3),
                "recall": round(cat_rep.get("recall", 0.0), 3),
                "f1_score": round(cat_rep.get("f1-score", 0.0), 3)
            }

        res = {
            "success": True,
            "algorithm": "TF-IDF (1-2 ngrams) + Multinomial Naive Bayes (alpha=0.2)",
            "train_sample_count": len(X_train),
            "test_sample_count": len(X_test),
            "total_samples": len(df),
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "labels": labels,
            "confusion_matrix": cm,
            "samples_per_category": samples_per_category,
            "random_seed": random_state,
            "test_split_ratio": test_size,
            "synthetic_data_notice": "Evaluation performed on a held-out test split (25%) using fixed random_state=42. Synthetic benchmark evaluation data is explicitly flagged and must not be misrepresented as real-world production accuracy."
        }
        self.evaluation_cache = res
        return res

    def load_model(self) -> bool:
        """Loads the trained model and vectorizer from disk if available."""
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
            try:
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                self.is_trained = True
                self.classes_ = list(self.model.classes_)
                return True
            except Exception:
                self.is_trained = False
                return False
        else:
            csv_file = DATA_DIR / "training_data.csv"
            if os.path.exists(csv_file):
                res = self.train(str(csv_file))
                return res.get("success", False)
            self.is_trained = False
            return False

    def predict(self, description: str) -> Tuple[str, float]:
        """Predicts the category and model prediction probability (confidence) for a single description."""
        if not self.is_trained or self.model is None or self.vectorizer is None:
            return "Others", 0.0

        clean_desc = self.clean_text(description)
        if not clean_desc:
            return "Others", 0.0

        vec = self.vectorizer.transform([clean_desc])
        probas = self.model.predict_proba(vec)[0]
        max_idx = probas.argmax()
        category = self.classes_[max_idx]
        confidence = float(probas[max_idx])

        return category, round(confidence, 2)

    def predict_top_k(self, description: str, k: int = 3) -> List[Dict[str, Any]]:
        """Returns the top-k predicted categories with genuine model prediction probabilities."""
        if not self.is_trained or self.model is None or self.vectorizer is None:
            return [{"category": "Others", "probability": 0.0}]

        clean_desc = self.clean_text(description)
        if not clean_desc:
            return [{"category": "Others", "probability": 0.0}]

        vec = self.vectorizer.transform([clean_desc])
        probas = self.model.predict_proba(vec)[0]
        top_indices = probas.argsort()[::-1][:k]
        return [
            {"category": self.classes_[idx], "probability": round(float(probas[idx]), 3)}
            for idx in top_indices
        ]

    def get_info(self) -> Dict[str, Any]:
        return {
            "is_trained": self.is_trained,
            "classes": self.classes_,
            "model_type": "Multinomial Naive Bayes + TF-IDF (n-gram: 1-2)",
            "vocabulary_size": len(self.vectorizer.vocabulary_) if self.vectorizer else 0
        }
