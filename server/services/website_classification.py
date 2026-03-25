"""
ExamGuard Pro - Website Classification Service
Categorizes websites based on Education, AI, Entertainment, Technology and Computer Apps
Inspired by classification-of-websites.ipynb
"""

from typing import List, Dict, Any, cast
import re

# Classification Rules (Keywords & Domains)
CATEGORIES = {
    "Education": {
        "domains": [
            "edu", "coursera.org", "udemy.com", "khanacademy.org", 
            "brilliant.org", "wolframalpha.com", "edx.org", "wikipedia.org",
            "google.com/search", "bing.com", "github.com", "stackoverflow.com",
            "codepen.io", "jsfiddle.net", "repl.it", "overleaf.com",
            "kaggle.com", "datasetsearch.research.google.com"
        ],
        "keywords": [
            "education", "learning", "tutorial", "course", "university", 
            "study", "lecture", "student", "academic", "search", "google", 
            "documentation", "api", "library", "framework", "coding", 
            "development", "dataset apps", "virtual editor", "editor", 
            "technology", "computer apps"
        ]
    },
    "AI": {
        "domains": [
            "openai.com", "chatgpt.com", "claude.ai", "huggingface.co", 
            "anthropic.com", "gemini.google.com", "perplexity.ai"
        ],
        "keywords": [
            "artificial intelligence", "ai", "machine learning", "chatbot", "gpt"
        ]
    },
    "Entertainment": {
        "domains": [
            "netflix.com", "youtube.com", "spotify.com", "twitch.tv", 
            "tiktok.com", "instagram.com", "facebook.com", "twitter.com",
            "amazon.com", "tripadvisor.com", "booking.com", "expedia.com"
        ],
        "keywords": [
            "movie", "film", "series", "music", "video", "videos", "shopping", 
            "travel", "social media", "fun", "game", "gaming", "streaming"
        ]
    }
}

class WebsiteClassifier:
    """Classify websites into predefined educational/productivity categories"""
    
    def __init__(self, config: Dict = None):
        self.config = config or CATEGORIES
    
    def extract_clean_text(self, url: str) -> str:
        """Extract potential descriptive text from URL and domain"""
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        # Replace non-alphanumeric with space
        url = re.sub(r'[^a-zA-Z0-9\.]', ' ', url)
        return url.lower()

    def classify(self, url: str, title: str = "") -> str:
        """
        Classify a website into one of the categories.
        Returns the primary category or 'Other'
        """
        clean_url = self.extract_clean_text(url)
        full_context = f"{clean_url} {title.lower() if title else ''}"
        
        matches = {cat: 0 for cat in self.config.keys()}
        
        for category, rules in self.config.items():
            # Check domains
            if "domains" in rules:
                for domain in rules["domains"]:
                    if domain in clean_url:
                        matches[category] += 10 # High weight for domain match
            
            # Check keywords
            if "keywords" in rules:
                for keyword in rules["keywords"]:
                    if keyword in full_context:
                        matches[category] += 1
        
        # Get category with highest score
        if any(v > 0 for v in matches.values()):
            primary_cat = max(matches.keys(), key=lambda k: matches[k])
            return str(primary_cat)
            
        return "General" # Fallback

# Singleton
classifier = WebsiteClassifier()

def get_website_category(url: str, title: str = "") -> str:
    """Helper to get website category from global classifier"""
    return classifier.classify(url, title)
