from typing import List, Dict, Any, Tuple
from app.schemas.statement import Transaction, ClassificationStats
from app.services.rule_classifier import RuleClassifier
from app.services.ml_classifier import MLClassifier

class ClassificationEngine:
    """
    Orchestrates non-LLM transaction classification combining:
    1. Custom Rules (User-defined highest priority)
    2. Predefined high-confidence rules
    3. Supervised ML (TF-IDF + Multinomial Naive Bayes)
    4. Fallback to Needs Review for low-confidence/uncertain descriptions.
    """

    def __init__(self):
        self.rule_engine = RuleClassifier()
        self.ml_engine = MLClassifier()

    def classify_transaction(self, txn: Transaction) -> Transaction:
        # If user has manually edited/corrected it, preserve manual override
        if txn.classification_method == "Manual Override":
            if not txn.explanation:
                txn.explanation = {
                    "category": txn.category,
                    "method": "Manual Override",
                    "confidence": 1.0,
                    "reason": "Manually corrected by user override."
                }
            return txn

        desc = txn.description or ""

        # Priority 1 & 2: Custom rules followed by predefined high-confidence rules
        rule_category, rule_confidence, matched_rule, rule_method = self.rule_engine.classify(desc, return_method=True)

        if rule_category:
            method_label = "Custom Rule" if rule_method == "Custom Rule" else "Rule-Based"
            txn.category = rule_category
            txn.classification_method = method_label
            txn.confidence = rule_confidence
            txn.explanation = {
                "category": rule_category,
                "method": method_label,
                "confidence": rule_confidence,
                "matched_keyword": matched_rule,
                "reason": f"Matched {rule_method.lower()} keyword '{matched_rule}'",
                "model_probabilities": []
            }
            if txn.review_status != "Needs Review":
                txn.review_status = "Verified" if rule_confidence >= 0.85 else "Needs Review"
            return txn

        # Priority 3: Traditional Supervised ML (TF-IDF + Multinomial Naive Bayes)
        top_k = self.ml_engine.predict_top_k(desc, k=3)
        ml_category = top_k[0]["category"] if top_k else "Others"
        ml_confidence = top_k[0]["probability"] if top_k else 0.0

        if self.ml_engine.is_trained and ml_confidence >= 0.45:
            txn.category = ml_category
            txn.classification_method = "ML"
            txn.confidence = ml_confidence
            txn.explanation = {
                "category": ml_category,
                "method": "ML",
                "confidence": ml_confidence,
                "matched_keyword": None,
                "reason": f"Predicted by Multinomial Naive Bayes (confidence: {int(ml_confidence * 100)}%)",
                "model_probabilities": top_k
            }
            if ml_confidence >= 0.70 and txn.review_status != "Needs Review":
                txn.review_status = "Verified"
            else:
                txn.review_status = "Needs Review"
            return txn

        # Priority 4: Low confidence / Uncertain fallback -> Needs Review
        txn.category = "Others"
        txn.classification_method = "ML" if self.ml_engine.is_trained else "Unclassified"
        txn.confidence = ml_confidence if self.ml_engine.is_trained else 0.0
        txn.explanation = {
            "category": "Others",
            "method": "ML" if self.ml_engine.is_trained else "Unclassified",
            "confidence": txn.confidence,
            "matched_keyword": None,
            "reason": f"Uncertain classification: top model probability ({int(ml_confidence * 100)}%) is below confidence threshold; requires audit.",
            "model_probabilities": top_k
        }
        txn.review_status = "Needs Review"
        return txn

    def classify_all(self, transactions: List[Transaction]) -> Tuple[List[Transaction], ClassificationStats]:
        classified = []
        rule_count = 0
        ml_count = 0
        needs_review_count = 0
        total_conf = 0.0
        cat_dist: Dict[str, int] = {}
        spend_dist: Dict[str, float] = {}

        conf_count = 0
        for t in transactions:
            updated_t = self.classify_transaction(t)
            classified.append(updated_t)

            if updated_t.classification_method in ["Rule-Based", "Custom Rule"]:
                rule_count += 1
            elif updated_t.classification_method == "ML":
                ml_count += 1

            if updated_t.review_status == "Needs Review":
                needs_review_count += 1

            if updated_t.confidence is not None:
                total_conf += updated_t.confidence
                conf_count += 1

            cat = updated_t.category
            cat_dist[cat] = cat_dist.get(cat, 0) + 1

            spend = (updated_t.debit or 0.0)
            spend_dist[cat] = spend_dist.get(cat, 0.0) + spend

        total = len(classified)
        stats = ClassificationStats(
            total_classified=total,
            rule_based_count=rule_count,
            rule_based_pct=round((rule_count / total * 100), 1) if total > 0 else 0.0,
            ml_count=ml_count,
            ml_pct=round((ml_count / total * 100), 1) if total > 0 else 0.0,
            needs_review_count=needs_review_count,
            needs_review_pct=round((needs_review_count / total * 100), 1) if total > 0 else 0.0,
            average_confidence=round((total_conf / conf_count), 2) if conf_count > 0 else 0.0,
            category_distribution=cat_dist,
            spend_by_category={k: round(v, 2) for k, v in spend_dist.items()}
        )

        return classified, stats
