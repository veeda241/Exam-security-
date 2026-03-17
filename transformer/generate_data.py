"""
ExamGuard Pro - Training Data Generator
Generates labeled datasets for:
  1. URL/Website Risk Classification
  2. Behavioral Sequence Anomaly Detection
  3. Screen Content Risk Classification

All data is synthetic + seeded from the project's existing config lists.
"""

import random
import json
from typing import List, Tuple, Dict
from pathlib import Path


# ============================================================================
# URL RISK CLASSIFICATION DATA
# ============================================================================

# Category -> (risk_score 0-1, list of domains/URLs)
URL_CATEGORIES: Dict[str, Tuple[float, List[str]]] = {
    "ai_tool": (0.90, [
        "chat.openai.com", "chatgpt.com", "openai.com",
        "gemini.google.com", "bard.google.com",
        "claude.ai", "anthropic.com",
        "perplexity.ai", "perplexity.ai/search",
        "copilot.microsoft.com", "bing.com/chat",
        "poe.com", "character.ai",
        "huggingface.co/chat", "deepseek.com", "deepseek.com/chat",
        "you.com", "phind.com",
        "wolframalpha.com", "symbolab.com",
        "photomath.com", "mathway.com",
        "writesonic.com", "jasper.ai",
        "grammarly.com/ai", "quillbot.com",
        "chat.mistral.ai", "groq.com",
        "together.ai", "replicate.com",
        "cohere.com/chat", "cohere.com",
        "labs.google.com/ai", "aistudio.google.com",
        "gamma.app", "tome.app",
    ]),
    "cheating": (0.95, [
        "chegg.com", "chegg.com/homework-help",
        "coursehero.com", "coursehero.com/tutors",
        "studocu.com", "studocu.com/document",
        "quizlet.com", "quizlet.com/flashcards",
        "brainly.com", "brainly.in",
        "bartleby.com", "bartleby.com/solution-answer",
        "numerade.com", "numerade.com/ask",
        "slader.com", "litanswers.org",
        "enotes.com", "cliffsnotes.com",
        "sparknotes.com",
        "wyzant.com", "tutor.com",
        "photomath.com/practice",
        "socratic.org",
        "homeworklib.com", "assignmentexpert.com",
        "essaytyper.com", "essaybot.com",
        "paperrater.com",
    ]),
    "entertainment": (0.60, [
        "youtube.com", "youtube.com/watch",
        "netflix.com", "netflix.com/browse",
        "hulu.com", "disneyplus.com", "primevideo.com",
        "twitch.tv", "kick.com",
        "tiktok.com", "tiktok.com/foryou",
        "instagram.com", "instagram.com/reels",
        "facebook.com", "twitter.com", "x.com",
        "reddit.com", "reddit.com/r/popular",
        "tumblr.com", "pinterest.com",
        "snapchat.com", "discord.com",
        "spotify.com", "music.youtube.com", "soundcloud.com",
        "store.steampowered.com", "epicgames.com",
        "crunchyroll.com", "roblox.com",
        "9gag.com", "imgur.com",
        "buzzfeed.com", "boredpanda.com",
        "twitch.tv/directory",
    ]),
    "social_media": (0.45, [
        "facebook.com/groups", "facebook.com/messenger",
        "messenger.com",
        "wa.me", "web.whatsapp.com",
        "telegram.org", "web.telegram.org",
        "signal.org",
        "slack.com", "teams.microsoft.com",
        "linkedin.com", "linkedin.com/messaging",
        "quora.com",
    ]),
    "code_hosting": (0.35, [
        "github.com", "github.com/search",
        "gitlab.com",
        "bitbucket.org",
        "pastebin.com", "hastebin.com",
        "codepen.io", "jsfiddle.net",
        "replit.com", "codesandbox.io",
        "stackblitz.com",
    ]),
    "educational": (0.10, [
        "docs.python.org", "docs.python.org/3",
        "developer.mozilla.org", "developer.mozilla.org/en-US/docs",
        "w3schools.com",
        "geeksforgeeks.org",
        "tutorialspoint.com",
        "khanacademy.org",
        "coursera.org", "edx.org",
        "udemy.com", "udacity.com",
        "mit.edu", "stanford.edu",
        "arxiv.org",
        "scholar.google.com",
        "researchgate.net",
        "britannica.com",
        "mathsisfun.com",
        "purplemath.com",
        "learn.microsoft.com",
        "docs.oracle.com",
        "cppreference.com",
    ]),
    "search_engine": (0.15, [
        "google.com", "google.com/search",
        "bing.com", "bing.com/search",
        "duckduckgo.com",
        "yahoo.com",
        "ecosia.org",
        "brave.com/search",
    ]),
    "exam_platform": (0.0, [
        "exam.google.com",
        "forms.google.com",
        "classroom.google.com",
        "canvas.instructure.com",
        "blackboard.com",
        "moodle.org",
        "turnitin.com",
        "respondus.com",
        "proctoru.com", "proctorio.com",
        "examsoft.com",
        "gradescope.com",
    ]),
}

# URL pattern templates for augmentation
URL_TEMPLATES = [
    "https://www.{domain}",
    "https://{domain}",
    "http://{domain}",
    "https://www.{domain}/some-page",
    "https://{domain}/path/to/page",
    "{domain}",
    "www.{domain}",
]


def generate_url_dataset() -> List[Dict]:
    """
    Generate URL classification dataset.
    Returns list of {url, domain, category, risk_score, label_id}
    """
    LABEL_MAP = {
        "exam_platform": 0,
        "educational": 1,
        "search_engine": 2,
        "code_hosting": 3,
        "social_media": 4,
        "entertainment": 5,
        "ai_tool": 6,
        "cheating": 7,
    }

    dataset = []

    for category, (risk_score, domains) in URL_CATEGORIES.items():
        label_id = LABEL_MAP[category]
        for domain in domains:
            # Base entry
            dataset.append({
                "url": f"https://{domain}",
                "domain": domain.split("/")[0],
                "category": category,
                "risk_score": risk_score,
                "label_id": label_id,
            })
            # Augmented variations
            for template in random.sample(URL_TEMPLATES, min(3, len(URL_TEMPLATES))):
                aug_url = template.format(domain=domain)
                dataset.append({
                    "url": aug_url,
                    "domain": domain.split("/")[0],
                    "category": category,
                    "risk_score": risk_score,
                    "label_id": label_id,
                })

    random.shuffle(dataset)
    return dataset


# ============================================================================
# ============================================================================
# BEHAVIORAL SEQUENCE ANOMALY DETECTION DATA
# ============================================================================

# Event types that the extension tracks (from eventLogger.js + background.js)
EVENT_TYPES = [
    "FOCUS",           # Student is on exam tab
    "TAB_SWITCH",      # Switched away from exam tab
    "COPY",            # Copied text
    "PASTE",           # Pasted text
    "VISIBILITY_CHANGE",  # Tab became hidden/visible
    "URL_VISIT",       # Visited a URL (with category info)
    "WINDOW_BLUR",     # Window lost focus
    "FACE_ABSENT",     # Face not detected by webcam
    "FACE_PRESENT",    # Face detected
    "FULLSCREEN_EXIT", # Exited fullscreen mode
    "RIGHT_CLICK",     # Right-click attempt
    "DEVTOOLS_OPEN",   # DevTools detected open
    "SCREEN_SHARE_STOPPED",  # Screen sharing was stopped
    "FORBIDDEN_SITE",  # Visited a forbidden/flagged site
    "TYPING",          # Student is typing (normal activity)
    "CLICK",           # Mouse click on exam page
    "SCROLL",          # Scrolling the exam page
    "IDLE",            # No activity detected
]

# Numeric ID for each event type (used as token in the transformer)
EVENT_TO_ID = {e: i + 4 for i, e in enumerate(EVENT_TYPES)}  # Reserve 0-3 for PAD/UNK/BOS/EOS

# URL risk categories attached to URL_VISIT events
URL_RISK_TAGS = ["safe", "low", "medium", "high", "critical"]


def _random_interval(base_ms: int = 5000, jitter: float = 0.5) -> int:
    """Random time interval in ms with jitter."""
    return max(500, int(base_ms * (1 + random.uniform(-jitter, jitter))))


def _generate_normal_sequence(length: int = 40) -> List[Dict]:
    """Generate a normal exam-taking behavior sequence (low risk)."""
    seq = []
    for _ in range(length):
        # Normal activity: mostly focus, typing, clicking, scrolling, face present
        event = random.choices(
            ["FOCUS", "TYPING", "CLICK", "SCROLL", "FACE_PRESENT",
             "VISIBILITY_CHANGE", "IDLE"],
            weights=[15, 30, 20, 15, 10, 5, 5],
            k=1
        )[0]
        seq.append({"event": event, "interval_ms": _random_interval(3000)})
    # Possibly 0-1 tab switch (very minor)
    if random.random() < 0.3:
        idx = random.randint(5, len(seq) - 5)
        seq.insert(idx, {"event": "TAB_SWITCH", "interval_ms": _random_interval(2000)})
        seq.insert(idx + 1, {"event": "FOCUS", "interval_ms": _random_interval(4000)})
    return seq


def _generate_mildly_suspicious(length: int = 40) -> List[Dict]:
    """Generate mildly suspicious behavior (medium risk)."""
    seq = []
    for _ in range(length):
        event = random.choices(
            ["FOCUS", "TYPING", "CLICK", "SCROLL", "FACE_PRESENT",
             "TAB_SWITCH", "VISIBILITY_CHANGE", "WINDOW_BLUR",
             "FACE_ABSENT", "IDLE"],
            weights=[12, 20, 12, 10, 8, 10, 8, 5, 5, 10],
            k=1
        )[0]
        seq.append({"event": event, "interval_ms": _random_interval(2500)})

    # Add some copy-paste attempts
    for _ in range(random.randint(1, 3)):
        idx = random.randint(3, len(seq) - 3)
        seq.insert(idx, {"event": "COPY", "interval_ms": _random_interval(1500)})

    # A few url visits (low/medium risk)
    for _ in range(random.randint(1, 2)):
        idx = random.randint(5, len(seq) - 3)
        seq.insert(idx, {"event": "URL_VISIT", "interval_ms": _random_interval(2000),
                         "url_risk": random.choice(["low", "medium"])})
    return seq


def _generate_highly_suspicious(length: int = 40) -> List[Dict]:
    """Generate highly suspicious cheating behavior (high risk)."""
    seq = []
    for _ in range(length):
        event = random.choices(
            ["FOCUS", "TYPING", "CLICK", "TAB_SWITCH",
             "VISIBILITY_CHANGE", "WINDOW_BLUR", "FACE_ABSENT",
             "COPY", "PASTE", "IDLE"],
            weights=[5, 10, 5, 15, 12, 10, 15, 10, 8, 10],
            k=1
        )[0]
        seq.append({"event": event, "interval_ms": _random_interval(1500)})

    # Rapid tab-switching burst
    burst_pos = random.randint(5, len(seq) - 10)
    for i in range(random.randint(3, 6)):
        seq.insert(burst_pos + i, {"event": "TAB_SWITCH", "interval_ms": _random_interval(800, 0.3)})

    # Forbidden site visits
    for _ in range(random.randint(1, 3)):
        idx = random.randint(3, len(seq) - 3)
        seq.insert(idx, {"event": "FORBIDDEN_SITE", "interval_ms": _random_interval(2000)})

    # URL visits to high-risk sites
    for _ in range(random.randint(2, 4)):
        idx = random.randint(3, len(seq) - 3)
        seq.insert(idx, {"event": "URL_VISIT", "interval_ms": _random_interval(1500),
                         "url_risk": random.choice(["high", "critical"])})

    # Face absent streaks
    absent_pos = random.randint(10, len(seq) - 10)
    for i in range(random.randint(3, 7)):
        seq.insert(absent_pos + i, {"event": "FACE_ABSENT", "interval_ms": _random_interval(5000)})

    return seq


def _generate_critical_cheating(length: int = 40) -> List[Dict]:
    """Generate critical cheating behavior (critical risk)."""
    seq = []
    for _ in range(length):
        event = random.choices(
            ["TAB_SWITCH", "WINDOW_BLUR", "FACE_ABSENT",
             "COPY", "PASTE", "FORBIDDEN_SITE", "URL_VISIT",
             "VISIBILITY_CHANGE", "FOCUS", "TYPING"],
            weights=[15, 10, 15, 10, 10, 10, 10, 8, 7, 5],
            k=1
        )[0]
        seq.append({"event": event, "interval_ms": _random_interval(1000)})

    # DevTools or screen share stopped
    if random.random() < 0.5:
        seq.insert(random.randint(5, len(seq) - 3),
                   {"event": "DEVTOOLS_OPEN", "interval_ms": _random_interval(1000)})
    if random.random() < 0.5:
        seq.insert(random.randint(5, len(seq) - 3),
                   {"event": "SCREEN_SHARE_STOPPED", "interval_ms": _random_interval(1000)})

    # Fullscreen exit
    for _ in range(random.randint(1, 3)):
        seq.insert(random.randint(3, len(seq) - 3),
                   {"event": "FULLSCREEN_EXIT", "interval_ms": _random_interval(1000)})

    # Many right-clicks (trying to copy)
    for _ in range(random.randint(2, 5)):
        seq.insert(random.randint(3, len(seq) - 3),
                   {"event": "RIGHT_CLICK", "interval_ms": _random_interval(800)})

    # Lots of forbidden/critical URL visits
    for _ in range(random.randint(3, 6)):
        idx = random.randint(3, len(seq) - 3)
        seq.insert(idx, {"event": "FORBIDDEN_SITE", "interval_ms": _random_interval(1000)})

    # Many paste events (pasting answers from outside)
    for _ in range(random.randint(3, 6)):
        seq.insert(random.randint(3, len(seq) - 3),
                   {"event": "PASTE", "interval_ms": _random_interval(1000)})

    return seq


def generate_behavior_dataset(n_per_class: int = 300) -> List[Dict]:
    """
    Generate behavioral sequences for anomaly detection.
    Returns list of {events: [...], risk_label: 0-3, risk_name: str}

    Labels:
      0 = normal   (0.0 risk)
      1 = mild     (0.3 risk)
      2 = high     (0.7 risk)
      3 = critical (1.0 risk)
    """
    dataset = []
    generators = [
        (0, "normal", _generate_normal_sequence),
        (1, "mild", _generate_mildly_suspicious),
        (2, "high", _generate_highly_suspicious),
        (3, "critical", _generate_critical_cheating),
    ]

    for label, name, gen_fn in generators:
        for _ in range(n_per_class):
            seq_len = random.randint(25, 60)
            events = gen_fn(length=seq_len)
            dataset.append({
                "events": events,
                "risk_label": label,
                "risk_name": name,
            })

    random.shuffle(dataset)
    return dataset


# ============================================================================
# SCREEN CONTENT RISK CLASSIFICATION DATA
# ============================================================================

def generate_screen_content_dataset() -> List[Dict]:
    """
    Generate labeled screen content / page title snippets.
    These represent OCR-captured text or page titles from screenshots.
    Returns list of {text, category, risk_label}

    Categories:
      0 = exam_safe      (exam platform, educational)
      1 = low_risk       (search engine, docs)
      2 = medium_risk    (social media, code hosting)
      3 = high_risk      (entertainment, gaming)
      4 = critical_risk  (AI tools, cheating sites)
    """
    data = []

    # 0 - EXAM SAFE
    exam_safe = [
        "Canvas - Submit Assignment",
        "Google Forms - Midterm Exam",
        "Moodle - Quiz: Chapter 5",
        "Blackboard - Test 2 Submission",
        "Gradescope - Upload Answers",
        "Turnitin - Exam Integrity Check",
        "Respondus LockDown Browser - Secure Exam",
        "Google Classroom - Exam Active",
        "ProctorU - Exam in Progress",
        "ExamSoft - Assessment Window",
        "Your exam has been submitted successfully",
        "Time remaining: 45 minutes",
        "Question 12 of 50 - Multiple Choice",
        "Select the best answer from the options below",
        "Please read each question carefully before answering",
        "Exam Instructions: You have 90 minutes to complete",
        "Submit Quiz - Are you sure?",
        "Proctorio - Exam monitoring active",
        "Safe Exam Browser - Locked Mode",
        "Khan Academy - Practice Quiz",
        "Coursera - Graded Assessment",
        "edX - Certificates Exam",
        "Python Official Documentation - Functions",
        "MDN Web Docs - Array.prototype.map()",
        "W3Schools - SQL Tutorial",
        "GeeksforGeeks - Data Structures",
        "Learn Microsoft - Azure Fundamentals",
        "Stanford Online - Machine Learning",
        "MIT OpenCourseWare - Calculus",
        "Academic paper: Neural Networks for NLP",
        "Textbook: Introduction to Algorithms, Chapter 4",
        "Lecture slides - Organic Chemistry",
        "University Library - Research Database",
        "Google Scholar - Search Results",
        "IEEE Xplore - Conference Paper",
        "ResearchGate - Article Download",
    ]

    # 1 - LOW RISK
    low_risk = [
        "Google - search results for python list comprehension",
        "Bing - how to calculate derivatives",
        "DuckDuckGo - search results",
        "Wikipedia - Photosynthesis",
        "Wikipedia - World War II",
        "Stack Overflow - How to reverse a string in Python",
        "Stack Overflow - SQL JOIN explained",
        "Programiz - Python For Loop",
        "TutorialsPoint - Java Basics",
        "cppreference.com - std::vector",
        "docs.oracle.com - Java SE Documentation",
        "Real Python - List Comprehensions",
        "Encyclopaedia Britannica - Cell Biology",
        "National Geographic - Climate Change",
        "Calculator.net - Scientific Calculator",
        "Wolfram MathWorld - Integral Calculus",
        "Dictionary.com - Definition of osmosis",
    ]

    # 2 - MEDIUM RISK
    medium_risk = [
        "GitHub - student123/exam-notes repository",
        "GitHub - Search results for algorithm solutions",
        "GitLab - Project Files",
        "Pastebin - Untitled paste",
        "CodePen - JavaScript snippet",
        "Replit - Python project",
        "LinkedIn - Messaging",
        "Quora - What is the answer to question 5",
        "Slack - #study-group channel",
        "Microsoft Teams - Chat",
        "WhatsApp Web - Messages",
        "Telegram Web - Chat",
        "Discord - Server: Study Help",
        "Facebook Messenger - Active now",
        "Signal - Conversation",
    ]

    # 3 - HIGH RISK
    high_risk = [
        "YouTube - How to solve calculus problems fast",
        "YouTube - Exam answers leaked 2024",
        "Netflix - Currently watching",
        "Twitch - Live streaming",
        "Reddit - r/HomeworkHelp",
        "Reddit - r/CheatSheets",
        "TikTok - For You Page",
        "Instagram - Stories",
        "Twitter/X - Timeline",
        "Spotify - Now Playing",
        "Steam - Game Library",
        "Epic Games - Fortnite",
        "Pinterest - Study aesthetic",
        "Snapchat - Chat",
        "9GAG - Trending",
        "BuzzFeed - Quiz",
    ]

    # 4 - CRITICAL RISK (AI tools & cheating sites)
    critical_risk = [
        "ChatGPT - Chat with GPT-4",
        "ChatGPT - Solve this math problem",
        "Claude AI - Help me write an essay",
        "Gemini - Google AI Assistant",
        "Perplexity AI - Answer Engine",
        "Copilot - Microsoft AI",
        "Phind - AI Search for Developers",
        "You.com - AI Chat",
        "Poe - Ask AI anything",
        "WolframAlpha - Computational Answers",
        "Symbolab - Math Solver",
        "Mathway - Step by Step Solutions",
        "PhotoMath - Scan and Solve",
        "QuillBot - Paraphrase Text",
        "Grammarly AI - Rewrite my answer",
        "Chegg Study - Homework Help Solutions",
        "Chegg - Expert Q&A Answer",
        "Course Hero - Document: Final Exam Answers",
        "Course Hero - Tutor Chat",
        "Studocu - Past Exam Papers with Answers",
        "Brainly - Get Free Homework Help",
        "Bartleby - Textbook Solutions Step by Step",
        "Numerade - Video Step-by-Step Solutions",
        "Slader - Free Textbook Answers",
        "Essay Typer - Auto-generate essays",
        "EssayBot - AI Essay Writer",
        "AssignmentExpert - Solved Problems",
        "HomeworkLib - Free Answers",
        "View the full answer and unlock step-by-step solutions",
        "Upload your assignment for expert help",
        "Get unstuck with AI-powered homework help",
        "As an AI language model, here is the answer to your question",
        "Certainly! Let me solve this step by step for you",
        "Sure, I can help you with that exam question",
        "Here is the complete solution to problem 7",
    ]

    categories = [
        (exam_safe, 0, "exam_safe"),
        (low_risk, 1, "low_risk"),
        (medium_risk, 2, "medium_risk"),
        (high_risk, 3, "high_risk"),
        (critical_risk, 4, "critical_risk"),
    ]

    for texts, label, name in categories:
        for text in texts:
            data.append({"text": text, "category": name, "risk_label": label})
            # Lowercase augmentation
            data.append({"text": text.lower(), "category": name, "risk_label": label})
            # Add slight variation
            if random.random() < 0.5:
                data.append({"text": text + " - Page 1", "category": name, "risk_label": label})

    random.shuffle(data)
    return data


def save_datasets(output_dir: str = None):
    """Save all datasets to JSON files."""
    if output_dir is None:
        output_dir = str(Path(__file__).parent / "data")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # URL dataset
    url_data = generate_url_dataset()
    with open(Path(output_dir) / "url_dataset.json", "w") as f:
        json.dump(url_data, f, indent=2)
    print(f"URL dataset: {len(url_data)} samples saved")

    # Behavioral sequence dataset
    behavior_data = generate_behavior_dataset(n_per_class=300)
    with open(Path(output_dir) / "behavior_dataset.json", "w") as f:
        json.dump(behavior_data, f, indent=2)
    print(f"Behavior dataset: {len(behavior_data)} sequences saved")

    # Screen content dataset
    screen_data = generate_screen_content_dataset()
    with open(Path(output_dir) / "screen_content_dataset.json", "w") as f:
        json.dump(screen_data, f, indent=2)
    print(f"Screen content dataset: {len(screen_data)} samples saved")


if __name__ == "__main__":
    save_datasets()
