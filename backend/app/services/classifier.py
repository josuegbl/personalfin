from __future__ import annotations

import re
from collections import Counter, defaultdict

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sqlalchemy.orm import Session

from app.core.category_catalog import CATEGORY_CODE_SIN_CATEGORIA
from app.models.category import Category
from app.models.transaction import Transaction

_KEYWORD_DOMINANCE_THRESHOLD: float = 0.95
_KEYWORD_MIN_OCCURRENCES: int = 2
_KEYWORD_MIN_TOKEN_LENGTH: int = 4
# Subcategory names shorter than this are too generic for substring matching.
_CATEGORY_NAME_MIN_LENGTH: int = 5


class TransactionClassifier:
    """Classifies uncategorized transactions using transactions already classified by the user.

    Uses three complementary strategies in order:
    1. Category-name matching: subcategory names (e.g. "Spotify") are searched as
       substrings in the transaction text — works even with zero prior examples.
    2. Keyword pre-pass: tokens that appear ≥95% of the time in one category in the
       training data are treated as deterministic rules.
    3. TF-IDF + LinearSVC fallback: a calibrated ML model predicts the category;
       predictions below the confidence threshold are left unclassified.
    """

    CONFIDENCE_THRESHOLD: float = 0.70
    MIN_SAMPLES_PER_CLASS: int = 3
    MIN_TOTAL_SAMPLES: int = 10

    def classify_unclassified(self, db: Session) -> tuple[int, int]:
        """Train on classified transactions and predict for uncategorized ones.

        Args:
            db: Active SQLAlchemy session.

        Returns:
            Tuple of (classified_count, skipped_count).
        """
        sin_cat_id = self._sin_categoria_id(db)
        if sin_cat_id is None:
            return 0, 0

        category_rules = self._build_category_name_rules(db, sin_cat_id)
        texts, labels = self._load_training_data(db, sin_cat_id)
        keyword_map = self._build_keyword_map(texts, labels)
        model, vectorizer = self._train(texts, labels)

        return self._predict_and_assign(
            db, sin_cat_id, category_rules, keyword_map, model, vectorizer
        )

    def _sin_categoria_id(self, db: Session) -> int | None:
        cat = (
            db.query(Category)
            .filter(Category.codigo_sistema == CATEGORY_CODE_SIN_CATEGORIA)
            .first()
        )
        return cat.id if cat else None

    def _transaction_text(self, t: Transaction) -> str:
        parts = [t.concepto_original]
        if t.comercio:
            parts.append(t.comercio)
        return " ".join(parts).lower()

    def _build_category_name_rules(
        self, db: Session, sin_cat_id: int
    ) -> list[tuple[re.Pattern[str], int]]:
        """Build substring-match rules from subcategory names.

        Only subcategories (padre_id IS NOT NULL) with names long enough to be
        unambiguous are included. Matches "SpotifyES" via "spotify", for example.

        Args:
            db: Active SQLAlchemy session.
            sin_cat_id: ID of the 'Sin categoría' category to exclude.

        Returns:
            List of (compiled pattern, category_id) tuples, longest names first
            so more specific rules take precedence.
        """
        subcategories = (
            db.query(Category)
            .filter(
                Category.padre_id.isnot(None),
                Category.id != sin_cat_id,
            )
            .all()
        )

        rules = []
        for cat in subcategories:
            name = cat.nombre.lower()
            if len(name) >= _CATEGORY_NAME_MIN_LENGTH:
                rules.append((re.compile(re.escape(name)), cat.id))

        rules.sort(key=lambda r: -len(r[0].pattern))
        return rules

    def _load_training_data(
        self, db: Session, sin_cat_id: int
    ) -> tuple[list[str], list[int]]:
        """Load manually classified transactions, excluding classes with too few samples.

        Args:
            db: Active SQLAlchemy session.
            sin_cat_id: ID of the 'Sin categoría' category to exclude.

        Returns:
            Parallel lists of (text_features, category_ids).
        """
        classified = (
            db.query(Transaction)
            .filter(
                Transaction.categoria_id.isnot(None),
                Transaction.categoria_id != sin_cat_id,
            )
            .all()
        )

        counts = Counter(t.categoria_id for t in classified)
        eligible_ids = {
            cat_id
            for cat_id, n in counts.items()
            if n >= self.MIN_SAMPLES_PER_CLASS
        }

        texts = []
        labels = []
        for t in classified:
            if t.categoria_id in eligible_ids:
                texts.append(self._transaction_text(t))
                labels.append(t.categoria_id)

        return texts, labels

    def _build_keyword_map(
        self, texts: list[str], labels: list[int]
    ) -> dict[str, int]:
        """Extract tokens overwhelmingly associated with a single category.

        A token qualifies when it appears in ≥_KEYWORD_MIN_OCCURRENCES transactions
        and ≥95% of those belong to the same category.

        Args:
            texts: Training transaction texts.
            labels: Corresponding category IDs.

        Returns:
            Mapping from token string to category ID.
        """
        token_counts: dict[str, Counter] = defaultdict(Counter)

        for text, label in zip(texts, labels):
            seen: set[str] = set()
            for token in text.split():
                if len(token) >= _KEYWORD_MIN_TOKEN_LENGTH and token not in seen:
                    token_counts[token][label] += 1
                    seen.add(token)

        keyword_map: dict[str, int] = {}
        for token, cat_counts in token_counts.items():
            total = sum(cat_counts.values())
            top_cat, top_count = cat_counts.most_common(1)[0]
            if (
                total >= _KEYWORD_MIN_OCCURRENCES
                and top_count / total >= _KEYWORD_DOMINANCE_THRESHOLD
            ):
                keyword_map[token] = top_cat

        return keyword_map

    def _train(
        self, texts: list[str], labels: list[int]
    ) -> tuple[CalibratedClassifierCV | None, TfidfVectorizer | None]:
        """Fit a calibrated text classifier.

        Args:
            texts: Transaction text features.
            labels: Corresponding category IDs.

        Returns:
            Fitted (model, vectorizer), or (None, None) if insufficient data.
        """
        if len(set(labels)) < 2 or len(texts) < self.MIN_TOTAL_SAMPLES:
            return None, None

        vectorizer = TfidfVectorizer(sublinear_tf=True, min_df=1, ngram_range=(1, 2))
        X = vectorizer.fit_transform(texts)

        base = LinearSVC(max_iter=2000, C=1.0)
        model = CalibratedClassifierCV(base, cv=3)
        model.fit(X, labels)

        return model, vectorizer

    def _predict_and_assign(
        self,
        db: Session,
        sin_cat_id: int,
        category_rules: list[tuple[re.Pattern[str], int]],
        keyword_map: dict[str, int],
        model: CalibratedClassifierCV | None,
        vectorizer: TfidfVectorizer | None,
    ) -> tuple[int, int]:
        """Predict categories for all uncategorized transactions and persist confident ones.

        Tries category-name matching first, then keyword rules, then the ML model.

        Args:
            db: Active SQLAlchemy session.
            sin_cat_id: ID of the 'Sin categoría' category.
            category_rules: Subcategory name patterns sorted longest-first.
            keyword_map: Deterministic token → category ID rules.
            model: Fitted classifier (may be None).
            vectorizer: Fitted TF-IDF vectorizer (may be None).

        Returns:
            Tuple of (classified_count, skipped_count).
        """
        unclassified = (
            db.query(Transaction)
            .filter(Transaction.categoria_id == sin_cat_id)
            .all()
        )

        classified_count = 0
        skipped_count = 0

        for t in unclassified:
            text = self._transaction_text(t)
            category_id: int | None = None

            for pattern, cat_id in category_rules:
                if pattern.search(text):
                    category_id = cat_id
                    break

            if category_id is None:
                for token in text.split():
                    if token in keyword_map:
                        category_id = keyword_map[token]
                        break

            if category_id is None and model is not None and vectorizer is not None:
                X = vectorizer.transform([text])
                probs = model.predict_proba(X)[0]
                max_prob = float(np.max(probs))
                if max_prob >= self.CONFIDENCE_THRESHOLD:
                    category_id = int(model.classes_[int(np.argmax(probs))])

            if category_id is not None:
                t.categoria_id = category_id
                classified_count += 1
            else:
                skipped_count += 1

        if classified_count:
            db.commit()

        return classified_count, skipped_count
