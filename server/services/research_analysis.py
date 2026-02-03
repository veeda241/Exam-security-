"""
ExamGuard Pro - Research Analysis Engine
Analyzes search patterns and categorizes research sources
"""
from typing import List, Dict

def analyze_research_journey(journey: List[Dict]) -> Dict:
    """
    Analyzes a student's sequence of visited sites
    journey: List of {url, title, dwell_time}
    """
    if not journey:
        return {"strategy": "None", "score": 0, "insights": []}

    categories = {
        "Documentation": 0,
        "Tutorial/Blog": 0,
        "Community (StackOverflow/Reddit)": 0,
        "General Search": 0,
        "Tools (GitHub/NPM)": 0
    }

    insights = []
    
    # Simple categorization logic
    for step in journey:
        url = step.get('url', '').lower()
        if 'docs.' in url or 'developer.mozilla.org' in url or 'python.org' in url:
            categories["Documentation"] += 1
        elif 'stackoverflow.com' in url or 'reddit.com' in url or 'github.com' in url and '/issues/' in url:
            categories["Community (StackOverflow/Reddit)"] += 1
        elif 'medium.com' in url or 'dev.to' in url or 'tutorial' in url:
            categories["Tutorial/Blog"] += 1
        elif 'google.com' in url or 'bing.com' in url:
            categories["General Search"] += 1
        elif 'github.com' in url:
            categories["Tools (GitHub/NPM)"] += 1

    # Determine strategy type
    max_cat = max(categories, key=categories.get)
    strategy = "Exploratory"
    if categories["Documentation"] > categories["General Search"]:
        strategy = "Documentation-First"
    elif categories["Community (StackOverflow/Reddit)"] > 3:
        strategy = "Community-Driven"
    elif categories["General Search"] > 10:
        strategy = "Search-Heavy"

    # Calculate efficiency score (mock logic)
    # Higher score if Documentation and Tools are used relative to General Search
    total_steps = len(journey)
    efficiency = ((categories["Documentation"] * 2 + categories["Tools (GitHub/NPM)"] * 1.5) / (total_steps + 1)) * 50
    efficiency = min(100, efficiency + 30) # Baseline

    if categories["Documentation"] > 0:
        insights.append("Student shows strong reliance on official documentation.")
    if categories["General Search"] > total_steps / 2:
        insights.append("Student may be struggling to find specific information directly.")

    return {
        "strategy": strategy,
        "efficiency_score": round(efficiency, 1),
        "source_diversity": len([c for c in categories.values() if c > 0]) / len(categories),
        "insights": insights,
        "breakdown": categories
    }
