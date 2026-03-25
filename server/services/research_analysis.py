from typing import List, Dict
import os
import sys

# Attempt to handle different import paths
try:
    from .website_classification import get_website_category
except (ImportError, ValueError):
    try:
        from services.website_classification import get_website_category
    except ImportError:
        # Fallback for some environments
        sys_path_dir = os.path.dirname(os.path.abspath(__file__))
        if sys_path_dir not in sys.path:
            sys.path.append(sys_path_dir)
        from website_classification import get_website_category

def analyze_research_journey(journey: List[Dict]) -> Dict:
    """
    Analyzes a student's sequence of visited sites with dynamic risk/effort scoring.
    journey: List of {url, title, dwell_time}
    """
    if not journey:
        return {"strategy": "None", "effort_score": 100.0, "browsing_risk_score": 0.0, "insights": []}

    counts = {
        "Education": 0,
        "AI": 0,
        "Entertainment": 0,
        "General": 0
    }

    insights = []
    total_steps = len(journey)
    
    # Categorize steps
    for step in journey:
        category = get_website_category(step.get('url', ''), step.get('title', ''))
        counts[category if category in counts else "General"] += 1

    # Base Scores
    # Entertainment is pure distraction (High Risk)
    entertainment_factor = counts["Entertainment"] / total_steps
    # Education is productive (High Effort)
    effort_raw = counts["Education"] / total_steps
    # AI and General are intermediate (Semi-Risk / Neutral)
    ai_factor = counts["AI"] / total_steps
    general_factor = counts["General"] / total_steps

    # 1. Base Effort Calculation (0-100)
    # Effort is primary driven by Education/Tech/Apps usage
    effort_score = effort_raw * 100.0
    
    # 2. Base Risk Calculation (0-100)
    # Risk is primary driven by Entertainment, with AI as semi-risk
    risk_score = (entertainment_factor * 100.0) + (ai_factor * 20.0)

    # 3. Dynamic Coupling (Inverse Relationship)
    # "if high risk, then effort must decrease"
    # we subtract a portion of risk from effort
    effort_final = max(0.0, effort_score - (risk_score * 0.5))
    
    # "if high effort, then risk must decrease"
    # we subtract a portion of effort from risk
    risk_final = max(0.0, risk_score - (effort_score * 0.3))

    # Boost effort if they are purely in Education
    if effort_raw > 0.8:
        effort_final = min(100.0, effort_final + 20.0)
        insights.append("Student is highly focused on educational resources.")

    # High risk insights
    if entertainment_factor > 0.3:
        insights.append("Frequent entertainment browsing detected, significantly reducing effort score.")
    if ai_factor > 0.5:
        insights.append("High reliance on AI observed (counted as semi-risk activity).")

    # Determine strategy
    if effort_raw > 0.6: strategy = "Academic Research"
    elif entertainment_factor > 0.4: strategy = "Distracted Browsing"
    elif ai_factor > 0.4: strategy = "AI-Assisted"
    else: strategy = "Variable Research"

    return {
        "strategy": strategy,
        "effort_score": float(f"{effort_final:.1f}"),
        "browsing_risk_score": float(f"{risk_final:.1f}"),
        "source_diversity": float(len([c for c in counts.values() if c > 0])) / float(len(counts)),
        "insights": insights,
        "breakdown": counts
    }
