"""
Backward-compatible wrapper — all classification now uses content/ML page_classifier.
"""

from services.page_classifier import classify_for_tracker, classify_page

__all__ = ["classify_site", "classify_for_tracker", "classify_page", "tracker_category"]


def classify_site(url: str, title: str = ""):
    result = classify_page(url, title)
    if result.tracker_category == "other" and result.confidence < 0.4:
        return None
    return {
        "category": result.category,
        "site": (title or url)[:80],
        "risk_level": result.risk_level,
    }


def tracker_category(url: str, title: str = ""):
    return classify_page(url, title).tracker_category
