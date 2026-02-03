"""
ExamGuard Pro - Domain Check Service
Checks website relevance for exam content
"""

from typing import Dict, Any, List
import re

# Allowed domains for exam (configurable)
ALLOWED_DOMAINS = [
    "google.com",
    "stackoverflow.com",
    "github.com",
    "w3schools.com",
    "developer.mozilla.org",
    "python.org",
    "docs.python.org",
]

# Forbidden domains
FORBIDDEN_DOMAINS = [
    "chegg.com",
    "coursehero.com",
    "quizlet.com",
    "brainly.com",
    "slader.com",
    "chat.openai.com",
    "claude.ai",
    "bard.google.com",
]


class DomainChecker:
    """Check domain relevance and safety"""
    
    def __init__(self, allowed: List[str] = None, forbidden: List[str] = None):
        self.allowed_domains = allowed or ALLOWED_DOMAINS
        self.forbidden_domains = forbidden or FORBIDDEN_DOMAINS
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            # Remove protocol
            url = re.sub(r'^https?://', '', url)
            # Get domain
            domain = url.split('/')[0]
            # Remove www
            domain = re.sub(r'^www\.', '', domain)
            return domain.lower()
        except Exception:
            return ""
    
    def is_allowed(self, url: str) -> bool:
        """Check if URL is in allowed list"""
        domain = self.extract_domain(url)
        return any(allowed in domain for allowed in self.allowed_domains)
    
    def is_forbidden(self, url: str) -> bool:
        """Check if URL is in forbidden list"""
        domain = self.extract_domain(url)
        return any(forbidden in domain for forbidden in self.forbidden_domains)
    
    def check_domain(self, url: str) -> Dict[str, Any]:
        """Full domain check"""
        domain = self.extract_domain(url)
        is_forbidden = self.is_forbidden(url)
        is_allowed = self.is_allowed(url)
        
        risk_score = 0
        status = "neutral"
        
        if is_forbidden:
            risk_score = 50
            status = "forbidden"
        elif is_allowed:
            risk_score = 0
            status = "allowed"
        else:
            risk_score = 10  # Unknown domain, slight risk
            status = "unknown"
        
        return {
            "domain": domain,
            "url": url,
            "status": status,
            "is_forbidden": is_forbidden,
            "is_allowed": is_allowed,
            "risk_score": risk_score
        }


# Singleton instance
domain_checker = DomainChecker()


async def check_domain_relevance(url: str) -> Dict[str, Any]:
    """Async wrapper for domain checking"""
    return domain_checker.check_domain(url)
